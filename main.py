import config
from database.db_manager import DBManager
from database.db_schema import init_db
from database.rtree_index import RTreeIndex
from database.spatial_cache import SpatialCache
from simulation.sumo_connector import SUMOConnector
from simulation.route_planner import RoutePlanner
from simulation.traffic_sampler import TrafficSampler
from dispatch.request_generator import RequestGenerator
from dispatch.scheduler import Scheduler
from rebalance.rebalance_executor import RebalanceExecutor
import sumolib
import os

def main():
    # 1. 初始化数据库表结构
    init_db()
    db = DBManager()
    
    # 2. 初始化路网规划器与空间缓存
    net = sumolib.net.readNet(config.NET_FILE)
    route_planner = RoutePlanner(config.NET_FILE)
    
    spatial_cache = SpatialCache()
    # 计算路网边界
    edges = net.getEdges()
    min_x = min_y = float('inf')
    max_x = max_y = float('-inf')
    for e in edges:
        shape = e.getShape()
        for x, y in shape:
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x)
            max_y = max(max_y, y)
    # 将 net 传递给 spatial_cache 以便进行 SUMO 坐标到经纬度的转换
    spatial_cache.set_network_bounds((min_x, max_x, min_y, max_y), net=net)
    
    # 3. 生成随机请求
    db.cursor.execute("SELECT COUNT(*) FROM trip_requests")
    if db.cursor.fetchone()[0] == 0:
        generator = RequestGenerator(db, route_planner, net)
        generator.generate()

    # 4. 启动 SUMO 仿真
    sumo = SUMOConnector(cfg_file=config.CFG_FILE)
    sumo.start()

    # 5. 初始化核心模块
    rtree = RTreeIndex(db)
    traffic_sampler = TrafficSampler(db, sample_interval=30)
    scheduler = Scheduler(db, rtree, sumo, route_planner, traffic_sampler)
    rebalancer = RebalanceExecutor(db, sumo, route_planner, traffic_sampler)

    # 8. 主循环
    seen_taxis = set()
    all_edges = net.getEdges()
    # 过滤掉内部边（以 ":" 开头的边）
    edge_ids = [e.getID() for e in all_edges if not e.getID().startswith(":")]
    
    # 筛选出主干道或通行能力较强的道路，用于背景车的目标选择，防止死锁
    major_edge_ids = []
    outer_major_edge_ids = [] # 专供背景车使用：外围且车道多的路
    
    # 新增：按照车道数分类的外围道路，用于精细化分流
    outer_lanes_4 = []
    outer_lanes_3 = []
    outer_lanes_2 = []
    
    for e in all_edges:
        if not e.getID().startswith(":"):
            # 获取路段中心坐标
            shape = e.getShape()
            xs, ys = zip(*shape)
            cx, cy = sum(xs)/len(xs), sum(ys)/len(ys)
            
            # 判断是否在中心区 (沿用 spatial_cache 的逻辑)
            center_x = (min_x + max_x) / 2
            center_y = (min_y + max_y) / 2
            radius_sq = ((max_x - min_x) * 0.25) ** 2
            dist_sq = (cx - center_x)**2 + (cy - center_y)**2
            is_center = dist_sq <= radius_sq

            lane_num = e.getLaneNumber()

            # 可以通过车道数或者限速来判断是否为主干道
            if lane_num >= 2 or e.getSpeed() >= 13.89: # 至少2车道，或限速>=50km/h
                major_edge_ids.append(e.getID())
                # 进一步筛选出不在市中心的、车道数多的优质外围主干道
                if not is_center:
                    if lane_num >= 2:
                        outer_major_edge_ids.append(e.getID())
                    if lane_num >= 4:
                        outer_lanes_4.append(e.getID())
                    elif lane_num == 3:
                        outer_lanes_3.append(e.getID())
                    elif lane_num == 2:
                        outer_lanes_2.append(e.getID())
                
    # 如果路网没有符合条件的主干道，退回全量边
    if not major_edge_ids:
        major_edge_ids = edge_ids
    if not outer_major_edge_ids:
        outer_major_edge_ids = major_edge_ids
    
    # 保证各层级列表不为空
    if not outer_lanes_4: outer_lanes_4 = outer_major_edge_ids
    if not outer_lanes_3: outer_lanes_3 = outer_major_edge_ids
    if not outer_lanes_2: outer_lanes_2 = outer_major_edge_ids

    def get_hierarchical_outer_edge():
        """按车道数权重选择外围道路：60%选4车道，30%选3车道，10%选2车道"""
        r = random.random()
        if r < 0.70:
            return random.choice(outer_lanes_4)
        elif r < 0.90:
            return random.choice(outer_lanes_3)
        else:
            return random.choice(outer_lanes_2)
    
    for step in range(config.STEPS):
        try:
            sumo.step()
        except Exception as e:
            import traceback; traceback.print_exc()
            break

        # 核心：提前续接路线，防止空闲车辆到达终点被 SUMO 自动删除
        import traci
        import random
        try:
            all_vehicles = traci.vehicle.getIDList()
            for vid in all_vehicles:
                if vid.startswith("bg_") or vid.startswith("taxi_"):
                    # 检查是否是纯粹的空闲状态 (只有 IDLE 才续接随机路线，REBALANCING 有明确目标不能续)
                    is_idle = True
                    if vid.startswith("taxi_"):
                        db.cursor.execute("SELECT status FROM taxis WHERE taxi_id=?", (vid,))
                        row = db.cursor.fetchone()
                        if row and row[0] != 'IDLE':
                            is_idle = False

                    if is_idle:
                        route = traci.vehicle.getRoute(vid)
                        route_index = traci.vehicle.getRouteIndex(vid)
                        # 如果空闲车辆快要到达路线终点，给它续一段随机路，防止被删除
                        if route_index >= len(route) - 2:
                            current_edge = traci.vehicle.getRoadID(vid)
                            if not current_edge.startswith(":"): # 不在交叉口内部
                                # 背景车优先选择主干道作为目的地，防止聚集在小路死锁
                                # V0.2: 进一步优化，按照概率分布引导背景车
                                # 85% 的概率去外围道路，15% 的概率去市中心道路，保证中心有少量车
                                if vid.startswith("bg_"):
                                    if random.random() < 0.85:
                                        # 去外围时，如果能拿到畅通列表就用畅通列表，否则按车道权重分配
                                        free_major_edges = traffic_sampler.get_free_edges(fallback_edges=None)
                                        if free_major_edges:
                                            # 从畅通列表里挑，但如果可能的话过滤出外围的
                                            outer_free = [e for e in free_major_edges if e in outer_major_edge_ids]
                                            end_edge = random.choice(outer_free if outer_free else free_major_edges)
                                        else:
                                            end_edge = get_hierarchical_outer_edge()
                                    else:
                                        # 去中心道路或者全图普通道路
                                        free_major_edges = traffic_sampler.get_free_edges(fallback_edges=major_edge_ids)
                                        end_edge = random.choice(free_major_edges)
                                else:
                                    end_edge = random.choice(edge_ids)
                                
                                is_bg = vid.startswith("bg_")
                                new_path = route_planner.get_shortest_path(current_edge, end_edge, is_bg_vehicle=is_bg)
                                if len(new_path) > 1:
                                    traci.vehicle.setRoute(vid, new_path)
        except Exception:
            pass

        # 备用方案：处理意外到达或因碰撞被移除的车辆（保证全场300辆出租车和背景车不减少）
        try:
            active_vehicles = set(traci.vehicle.getIDList())
            
            # 1. 恢复掉线的出租车
            db.cursor.execute("SELECT taxi_id, status FROM taxis")
            all_taxis = db.cursor.fetchall()
            
            for vid, status in all_taxis:
                if vid not in active_vehicles:
                    # 这辆车掉线了（可能到达终点，也可能因碰撞被 remove）
                    # 1. 如果它带着订单掉线，释放订单
                    if status != 'IDLE':
                        db.cursor.execute("UPDATE taxis SET status='IDLE' WHERE taxi_id=?", (vid,))
                        if hasattr(scheduler, 'active_assignments') and vid in scheduler.active_assignments:
                            req_id = scheduler.active_assignments[vid]
                            db.cursor.execute("UPDATE trip_requests SET status='PENDING' WHERE request_id=? AND status != 'COMPLETED'", (req_id,))
                            del scheduler.active_assignments[vid]
                        db.commit()

                    # 2. 重新将其加入仿真
                    try:
                        # 确保车辆真不在仿真中
                        if vid not in traci.vehicle.getIDList():
                            start_edge = random.choice(edge_ids)
                            end_edge = random.choice(edge_ids)
                            route = route_planner.get_shortest_path(start_edge, end_edge)
                            if len(route) < 2:
                                route = [start_edge]
                                
                            route_id = f"route_{vid}_{step}"
                            traci.route.add(route_id, route)
                            traci.vehicle.add(vid, routeID=route_id, typeID="taxi")
                            traci.vehicle.setColor(vid, (0, 255, 0, 255))
                            seen_taxis.discard(vid) # 允许重新初始化
                    except Exception:
                        pass
            
            # 2. 恢复掉线的背景车
            arrived_vehicles = traci.simulation.getArrivedIDList()
            for vid in arrived_vehicles:
                if vid.startswith("bg_"):
                    try:
                        if vid not in traci.vehicle.getIDList():
                            # 背景车重生逻辑：85%在远离中心的外围降生，15%在全图（包含中心）降生
                            if random.random() < 0.85:
                                start_edge = get_hierarchical_outer_edge()
                                end_edge = get_hierarchical_outer_edge()
                            else:
                                start_edge = random.choice(major_edge_ids)
                                end_edge = random.choice(major_edge_ids)
                                
                            route = route_planner.get_shortest_path(start_edge, end_edge, is_bg_vehicle=True)
                            if len(route) < 2:
                                route = [start_edge]
                                
                            route_id = f"route_{vid}_{step}"
                            traci.route.add(route_id, route)
                            traci.vehicle.add(vid, routeID=route_id, typeID="bg")
                    except Exception:
                        pass
        except Exception:
            pass

        # 获取出租车最新位置并更新数据库和 R‑Tree
        try:
            taxi_positions = sumo.get_taxi_positions()
        except Exception:
            taxi_positions = []
        
        for taxi_id, x, y in taxi_positions:
            # 初始化新出现的出租车为绿色
            if taxi_id not in seen_taxis:
                try:
                    import traci
                    from vehicle.vehicle_visual import VehicleVisual
                    VehicleVisual.set_color(taxi_id, 'IDLE')
                except Exception:
                    pass
                seen_taxis.add(taxi_id)

            # 获取车辆所在网格
            cell_id = spatial_cache.get_region_id(x, y)

            # 确保车辆在数据库中（如果是新出现的车辆，插入初始状态）
            db.cursor.execute("INSERT OR IGNORE INTO taxis (taxi_id, status, current_x, current_y, last_update, cell_id) VALUES (?, 'IDLE', ?, ?, ?, ?)",
                              (taxi_id, x, y, step, cell_id))
            # 更新最新位置和时间戳
            db.update_taxi_location(taxi_id, x, y, step, cell_id)
            rtree.update(taxi_id, x, y)
        db.commit()

        # V0.2: 采集交通状态快照
        traffic_sampler.sample(step)

        # 处理新产生的乘客请求
        scheduler.process_pending_requests(step)

        # 检查车辆到达事件
        for taxi_id, _, _ in taxi_positions:
            if not sumo.is_on_internal_edge(taxi_id):
                current_edge = sumo.get_vehicle_edge(taxi_id)
                scheduler.handle_arrival(taxi_id, current_edge, step)

        # 定期执行重平衡
        rebalancer.execute(step)

    # 10. 仿真结束，计算指标并输出
    db.cursor.execute("SELECT AVG(wait_time) FROM assignments WHERE wait_time IS NOT NULL")
    avg_wait = db.cursor.fetchone()[0]
    if avg_wait:
        print(f"Average Wait Time: {avg_wait:.2f} seconds")
    else:
        print("Average Wait Time: N/A (No trips completed)")

    # 关闭
    sumo.close()
    db.close()

if __name__ == "__main__":
    main()
