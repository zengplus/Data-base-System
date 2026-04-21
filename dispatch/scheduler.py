from database.db_manager import DBManager
from database.rtree_index import RTreeIndex
from simulation.sumo_connector import SUMOConnector
from simulation.route_planner import RoutePlanner
from dispatch.request_pool import RequestPool
from dispatch.knn_finder import KNNFinder
from dispatch.dispatch_assigner import DispatchAssigner
from dispatch.route_assigner import RouteAssigner
from vehicle.atomic_updater import AtomicUpdater
from vehicle.vehicle_visual import VehicleVisual
from dispatch.request_handler import generate_person_in_sumo
import config
import random

class Scheduler:
    """重构后的核心调度器 (V0.2)"""
    def __init__(self, db: DBManager, rtree: RTreeIndex, sumo: SUMOConnector, route_planner: RoutePlanner, traffic_sampler):
        self.db = db
        self.rtree = rtree
        self.sumo = sumo
        self.route_planner = route_planner
        self.traffic_sampler = traffic_sampler
        
        self.request_pool = RequestPool(db, timeout_steps=600)
        self.knn_finder = KNNFinder(rtree)
        self.dispatch_assigner = DispatchAssigner(sumo, route_planner, traffic_sampler)
        self.route_assigner = RouteAssigner(sumo)
        
        self.active_assignments = {}   # taxi_id -> request_id
        self.visible_persons = set()
        self.mode = config.EXPERIMENT_MODE

    def _select_best_taxi(self, current_step, ox, oy, origin_edge):
        """
        根据实验模式返回 (taxi_id, route_to_origin)
        - baseline: 随机空车
        - knn/proposed: KNN + 时间成本最优
        """
        if self.mode == "baseline":
            idle_taxis = self.db.get_idle_taxis(current_step)
            # 在 baseline 中，如果找不到空车，就让他等待，但我们也可以给随机策略一点小惩罚
            if not idle_taxis:
                return None, None
            
            # 使用固定的随机种子，保证 baseline 抽取一致
            r = random.Random(config.PYTHON_RANDOM_SEED + current_step)
            r.shuffle(idle_taxis)
            for taxi_id, *_ in idle_taxis:
                try:
                    if self.sumo.is_on_internal_edge(taxi_id):
                        continue
                    current_edge = self.sumo.get_vehicle_edge(taxi_id)
                    route = self.route_planner.get_shortest_path(current_edge, origin_edge)
                    if route and len(route) >= 1:
                        return taxi_id, route
                except Exception:
                    continue
            return None, None

        idle_taxis = self.knn_finder.find_nearest_idle_taxis(ox, oy, current_step, k=15)
        if not idle_taxis:
            return None, None
        return self.dispatch_assigner.find_best_taxi(idle_taxis, ox, oy, origin_edge)

    def process_pending_requests(self, current_step):
        """处理当前时间步所有待处理的请求，并清理超时死单"""
        # 1. 清理超时订单
        self._handle_timeouts(current_step)

        # 2. 获取仍在有效期内的请求
        requests = self.request_pool.get_pending_requests(current_step)

        for req_id, ox, oy, origin_edge, dest_edge in requests:
            # GUI 显示乘客
            if req_id not in self.visible_persons:
                import traci
                generate_person_in_sumo(traci, req_id, origin_edge, dest_edge, current_step)
                self.visible_persons.add(req_id)
                
            best_taxi_id, best_route = self._select_best_taxi(current_step, ox, oy, origin_edge)
            if not best_taxi_id:
                continue

            # 原子分配
            success = AtomicUpdater.assign_vehicle(self.db, best_taxi_id, req_id, current_step)
            if not success:
                continue

            self.active_assignments[best_taxi_id] = req_id
            self.route_assigner.assign_route(best_taxi_id, best_route)
            VehicleVisual.set_color(best_taxi_id, 'PICKUP')

    def _handle_timeouts(self, current_step):
        """处理所有类型的超时"""
        self.db.begin_transaction()
        try:
            cancelled_reqs = self.request_pool.get_timeout_pending_requests(current_step)
            self.request_pool.cancel_timeout_requests(current_step)

            stuck_reqs = self.request_pool.get_stuck_assignments(current_step)
            for req_id, taxi_id in stuck_reqs:
                cancelled_reqs.append((req_id,))
                AtomicUpdater.reset_to_idle(self.db, taxi_id)
                self.db.cursor.execute("UPDATE trip_requests SET status='CANCELLED' WHERE request_id=?", (req_id,))
                if taxi_id in self.active_assignments:
                    del self.active_assignments[taxi_id]

            self.db.commit()
            
            import traci
            for (req_id,) in cancelled_reqs:
                person_id = f"person_{req_id}"
                try:
                    if person_id in traci.person.getIDList():
                        traci.person.remove(person_id)
                except Exception:
                    pass
        except:
            self.db.rollback()

    def handle_arrival(self, taxi_id, current_edge, current_step):
        """处理车辆到达事件"""
        if taxi_id not in self.active_assignments:
            # 检查是否是重平衡到达
            self._check_rebalance_arrival(taxi_id, current_edge)
            return

        req_id = self.active_assignments[taxi_id]
        self.db.cursor.execute(
            "SELECT origin_edge, dest_edge, status FROM trip_requests WHERE request_id=?", (req_id,)
        )
        row = self.db.cursor.fetchone()
        if not row:
            return
        origin_edge, dest_edge, status = row

        if status == 'ASSIGNED' and current_edge == origin_edge:
            self._handle_pickup(taxi_id, req_id, current_edge, dest_edge, current_step)
        elif status == 'OCCUPIED' and current_edge == dest_edge:
            self._handle_dropoff(taxi_id, req_id, current_step)

    def _check_rebalance_arrival(self, taxi_id, current_edge):
        """如果车辆处于 REBALANCING 状态且没有活跃订单，可能是到达了重平衡目标"""
        self.db.cursor.execute("SELECT status FROM taxis WHERE taxi_id=?", (taxi_id,))
        row = self.db.cursor.fetchone()
        if row and row[0] == 'REBALANCING':
            # 简单策略：如果到了终点或者重平衡时间够长，恢复为 IDLE
            import traci
            try:
                route_index = traci.vehicle.getRouteIndex(taxi_id)
                route = traci.vehicle.getRoute(taxi_id)
                if route_index >= len(route) - 2:
                    AtomicUpdater.reset_to_idle(self.db, taxi_id)
                    VehicleVisual.set_color(taxi_id, 'IDLE')
            except Exception:
                pass

    def _handle_pickup(self, taxi_id, req_id, current_edge, dest_edge, current_step):
        self.db.begin_transaction()
        try:
            self.db.cursor.execute("UPDATE taxis SET status='OCCUPIED' WHERE taxi_id=?", (taxi_id,))
            self.db.cursor.execute("UPDATE trip_requests SET status='OCCUPIED' WHERE request_id=?", (req_id,))
            self.db.cursor.execute("UPDATE assignments SET pickup_time=? WHERE request_id=?", (current_step, req_id))
            self.db.commit()
        except:
            self.db.rollback()
            return

        try:
            import traci
            person_id = f"person_{req_id}"
            if person_id in traci.person.getIDList():
                traci.person.remove(person_id)
        except:
            pass

        route = self.route_planner.get_shortest_path(current_edge, dest_edge)
        self.route_assigner.assign_route(taxi_id, route)
        VehicleVisual.set_color(taxi_id, 'OCCUPIED')

    def _handle_dropoff(self, taxi_id, req_id, current_step):
        self.db.begin_transaction()
        try:
            self.db.cursor.execute("UPDATE taxis SET status='IDLE' WHERE taxi_id=?", (taxi_id,))
            self.db.cursor.execute("UPDATE trip_requests SET status='COMPLETED' WHERE request_id=?", (req_id,))
            self.db.cursor.execute(
                "UPDATE assignments SET dropoff_time=?, wait_time=? WHERE request_id=?",
                (current_step, current_step - self.db.cursor.execute(
                    "SELECT assign_time FROM assignments WHERE request_id=?", (req_id,)
                ).fetchone()[0], req_id)
            )
            self.db.commit()
            del self.active_assignments[taxi_id]
            VehicleVisual.set_color(taxi_id, 'IDLE')
        except:
            self.db.rollback()
