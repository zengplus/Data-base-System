from rebalance.supply_demand import SupplyDemand
from rebalance.travel_time_predictor import TravelTimePredictor
from rebalance.cost_matrix_builder import CostMatrixBuilder
from rebalance.min_cost_flow import MinCostFlow
from database.spatial_cache import SpatialCache
from vehicle.atomic_updater import AtomicUpdater
from vehicle.vehicle_visual import VehicleVisual
from dispatch.route_assigner import RouteAssigner
import config

class RebalanceExecutor:
    """执行 V0.2 最小成本流重平衡"""
    def __init__(self, db, sumo, route_planner, traffic_sampler):
        self.db = db
        self.sumo = sumo
        self.route_planner = route_planner
        self.traffic_sampler = traffic_sampler
        self.last_rebalance_step = 0
        
        self.supply_demand = SupplyDemand(db)
        self.time_predictor = TravelTimePredictor(traffic_sampler, route_planner)
        self.matrix_builder = CostMatrixBuilder(self.time_predictor)
        self.route_assigner = RouteAssigner(sumo)
        self.spatial_cache = SpatialCache()

    def execute(self, current_step):
        if current_step - self.last_rebalance_step < config.REBALANCE_INTERVAL:
            return
        self.last_rebalance_step = current_step

        supply, demand = self.supply_demand.compute(current_step)
        
        all_regions = set(supply.keys()).union(set(demand.keys()))
        
        target_demands = {}
        source_regions = set()
        
        for reg in all_regions:
            d = demand.get(reg, 0)
            s = supply.get(reg, 0)
            g = d - s
            if g > 0:
                target_demands[reg] = g
            elif g < 0:
                source_regions.add(reg)

        # 添加调试日志
        if current_step % (config.REBALANCE_INTERVAL * 2) == 0:
            print(f"[Rebalance Debug] Step {current_step}: 供需计算结果 -> 缺车区域数量: {len(target_demands)}, 富裕区域数量: {len(source_regions)}")

        if not target_demands or not source_regions:
            return

        # 收集富裕区域的空车列表
        idle_taxis_list = self.db.get_idle_taxis(current_step)
        
        # 降低重平衡的激进程度：
        # 1. 最多只允许调用当前空闲车辆的 10% (原为 20%)，保留更多空车给即时订单
        # 2. 如果全图空车少于 10 辆，则暂停重平衡，保证基本运力
        if len(idle_taxis_list) < 10:
            return
            
        max_rebalance_count = max(1, int(len(idle_taxis_list) * 0.1))
        
        # 即使只有1辆空车，也允许最多调度1辆（如果不足5辆的话，20%是0，用max(1, ...)保底）
        
        source_taxis = {} # region -> [taxi_ids]
        total_source_count = 0
        
        # 为了保证重平衡能够积极触发，我们不强求完全按照 source_regions 里的车来
        # 只要是空车，且所在的区域不是缺车区域（不在 target_demands 中），就可以被征用
        for taxi_id, x, y, cell_id in idle_taxis_list:
            if total_source_count >= max_rebalance_count:
                break
            # 放宽条件：只要当前区域不缺车，就可以作为提供者
            if cell_id not in target_demands:
                try:
                    if not self.sumo.is_on_internal_edge(taxi_id):
                        source_taxis.setdefault(cell_id, []).append(taxi_id)
                        total_source_count += 1
                        # 确保 source_regions 里有这个区域，否则后续算法匹配不到
                        source_regions.add(cell_id) 
                except Exception:
                    pass

        source_supplies = {reg: len(taxis) for reg, taxis in source_taxis.items()}

        # 构建成本矩阵并求解 MCF
        cost_matrix = self.matrix_builder.build(list(source_supplies.keys()), list(target_demands.keys()), db=self.db)
        instructions = MinCostFlow.solve(source_supplies, target_demands, cost_matrix)

        # 执行调度
        rebalance_count_this_step = 0
        for src, dst, count in instructions:
            if count <= 0: continue
            
            target_edge = self.spatial_cache.get_central_edge(dst)
            if not target_edge:
                # 如果没有中心边数据，尝试随机找一条边（Fallback）
                try:
                    target_edge = self.db.cursor.execute("SELECT origin_edge FROM trip_requests WHERE cell_id=? LIMIT 1", (dst,)).fetchone()
                    if target_edge: target_edge = target_edge[0]
                except:
                    pass
                if not target_edge:
                    continue

            taxis_to_move = source_taxis[src][:count]
            source_taxis[src] = source_taxis[src][count:] # 移除已调度的

            for taxi_id in taxis_to_move:
                try:
                    current_edge = self.sumo.get_vehicle_edge(taxi_id)
                    route = self.route_planner.get_shortest_path(current_edge, target_edge)
                    if len(route) >= 1:
                        success = AtomicUpdater.start_rebalance(self.db, taxi_id, src, dst, current_step)
                        if success:
                            self.route_assigner.assign_route(taxi_id, route)
                            VehicleVisual.set_color(taxi_id, 'REBALANCING')
                            rebalance_count_this_step += 1
                except Exception:
                    pass
        
        if rebalance_count_this_step > 0:
            print(f"[Rebalance] Step {current_step}: 触发了 {rebalance_count_this_step} 辆车的跨区域调度。")
