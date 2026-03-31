from database.db_manager import DBManager
from database.rtree_index import RTreeIndex
from simulation.sumo_connector import SUMOConnector
from simulation.route_planner import RoutePlanner
import config

from dispatch.request_handler import generate_person_in_sumo

class Scheduler:
    def __init__(self, db: DBManager, rtree: RTreeIndex, sumo: SUMOConnector, route_planner: RoutePlanner):
        self.db = db
        self.rtree = rtree
        self.sumo = sumo
        self.route_planner = route_planner
        self.active_assignments = {}   # taxi_id -> request_id (用于状态追踪)
        self.visible_persons = set()   # 记录已经在 GUI 中显示的 person
        self.order_timeout_steps = 600 # 订单等待超时时间（10分钟）

    def process_pending_requests(self, current_step):
        """处理当前时间步所有待处理的请求，并清理超时死单"""
        # 1. 首先清理超时的 PENDING 和接驾超时(ASSIGNED) 的死单
        self.db.begin_transaction()
        try:
            # 找到要取消的 PENDING 请求ID
            self.db.cursor.execute(
                "SELECT request_id FROM trip_requests WHERE status='PENDING' AND dispatch_time < ?",
                (current_step - self.order_timeout_steps,)
            )
            cancelled_reqs = self.db.cursor.fetchall()
            
            self.db.cursor.execute(
                "UPDATE trip_requests SET status='CANCELLED' WHERE status='PENDING' AND dispatch_time < ?",
                (current_step - self.order_timeout_steps,)
            )

            # 找到接驾超时的 ASSIGNED 请求（说明车卡死在路上永远过不来）
            self.db.cursor.execute(
                """SELECT r.request_id, a.taxi_id FROM trip_requests r 
                   JOIN assignments a ON r.request_id = a.request_id 
                   WHERE r.status='ASSIGNED' AND a.assign_time < ?""",
                (current_step - self.order_timeout_steps,)
            )
            stuck_reqs = self.db.cursor.fetchall()

            for req_id, taxi_id in stuck_reqs:
                cancelled_reqs.append((req_id,))
                # 释放这辆卡死的车
                self.db.cursor.execute("UPDATE taxis SET status='IDLE' WHERE taxi_id=?", (taxi_id,))
                self.db.cursor.execute("UPDATE trip_requests SET status='CANCELLED' WHERE request_id=?", (req_id,))
                # 移除活跃记录
                if taxi_id in self.active_assignments:
                    del self.active_assignments[taxi_id]

            self.db.commit()
            
            # 在 GUI 中移除这些超时等不到车的乘客
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

        # 2. 处理仍在有效期内的请求
        self.db.cursor.execute(
            "SELECT request_id, origin_x, origin_y, origin_edge, dest_edge FROM trip_requests WHERE status='PENDING' AND dispatch_time <= ?",
            (current_step,)
        )
        requests = self.db.cursor.fetchall()

        for req_id, ox, oy, origin_edge, dest_edge in requests:
            # 动态在 GUI 中显示这名乘客（如果还没显示的话）
            if req_id not in self.visible_persons:
                import traci
                generate_person_in_sumo(traci, req_id, origin_edge, dest_edge, current_step)
                self.visible_persons.add(req_id)
            # 找到最近的空闲出租车（KNN）
            # 缩减候选池，防止匹配到全城另一头的车
            idle_taxis = self.rtree.knn(ox, oy, current_step, k=15) 
            if not idle_taxis:
                continue

            best_taxi_id = None
            best_route = None
            
            # 首先，尝试寻找直接就在同一条边上的车（Pickup Time = 0）
            for taxi_id, _, _ in idle_taxis:
                try:
                    if not self.sumo.is_on_internal_edge(taxi_id):
                        current_edge = self.sumo.get_vehicle_edge(taxi_id)
                        if current_edge == origin_edge:
                            best_taxi_id = taxi_id
                            best_route = [current_edge]
                            break
                except Exception:
                    continue
                    
            # 如果同一条边上没有，再尝试寻找附近可以连通的车，以路径长度（接客时间）最短为准
            if not best_taxi_id:
                min_route_len = float('inf')
                for taxi_id, tx, ty in idle_taxis:
                    # 加入绝对的接驾物理直线距离限制：超过 1500 米（平方 2250000）的坚决不派！
                    dist_sq = (tx - ox)**2 + (ty - oy)**2
                    if dist_sq > 2250000:
                        continue

                    try:
                        if not self.sumo.is_on_internal_edge(taxi_id):
                            current_edge = self.sumo.get_vehicle_edge(taxi_id)
                            route = self.route_planner.get_shortest_path(current_edge, origin_edge)
                            
                            # 加入绝对的接驾导航距离限制：如果绕路超过 30 条边，坚决不派！
                            if len(route) >= 1 and len(route) < 30 and len(route) < min_route_len:
                                min_route_len = len(route)
                                best_taxi_id = taxi_id
                                best_route = route
                    except Exception:
                        continue
            
            if not best_taxi_id:
                continue

            # 原子分配
            success = self.db.assign_vehicle(best_taxi_id, req_id, current_step)
            if not success:
                continue

            # 记录活跃分配
            self.active_assignments[best_taxi_id] = req_id

            # 设置路线：从出租车当前位置到乘客出发地
            self.sumo.set_route(best_taxi_id, best_route)
            
            # 在 GUI 中将接驾中的出租车变色（可选：接驾可以用橙色或其他颜色，这里根据要求先不特别处理，但你可以自定义）
            # 我们先保持它为绿色，直到真正载客再变红
            try:
                import traci
                traci.vehicle.setColor(best_taxi_id, (255, 165, 0, 255)) # 橙色代表接驾
            except:
                pass

            # 注意：当车辆到达出发地时，我们需要再次设置路线到目的地，这将在主循环中通过检测车辆位置完成

    def handle_arrival(self, taxi_id, current_edge, current_step):
        """处理车辆到达上车点或目的地的事件"""
        if taxi_id not in self.active_assignments:
            return

        req_id = self.active_assignments[taxi_id]
        # 获取请求信息
        self.db.cursor.execute(
            "SELECT origin_edge, dest_edge, status FROM trip_requests WHERE request_id=?", (req_id,)
        )
        origin_edge, dest_edge, status = self.db.cursor.fetchone()

        if status == 'ASSIGNED' and current_edge == origin_edge:
            # 到达上车点：更新状态为 OCCUPIED，记录 pickup_time，设置路线到目的地
            self.db.begin_transaction()
            try:
                self.db.cursor.execute("UPDATE taxis SET status='OCCUPIED' WHERE taxi_id=?", (taxi_id,))
                self.db.cursor.execute("UPDATE trip_requests SET status='OCCUPIED' WHERE request_id=?", (req_id,))
                self.db.cursor.execute("UPDATE assignments SET pickup_time=? WHERE request_id=?", (current_step, req_id))
                self.db.commit()
            except:
                self.db.rollback()
                return

            # 在 GUI 中移除该 person，表示他上车了
            try:
                import traci
                person_id = f"person_{req_id}"
                if person_id in traci.person.getIDList():
                    traci.person.remove(person_id)
            except:
                pass

            # 设置路线到目的地
            route = self.route_planner.get_shortest_path(current_edge, dest_edge)
            if len(route) >= 1:
                self.sumo.set_route(taxi_id, route)
            
            # 载客状态变红
            try:
                import traci
                traci.vehicle.setColor(taxi_id, (255, 0, 0, 255)) # 红色
            except:
                pass

        elif status == 'OCCUPIED' and current_edge == dest_edge:
            # 到达目的地：释放车辆，记录 dropoff_time，计算等待时间
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
            except:
                self.db.rollback()
                
            # 恢复空闲状态变绿
            try:
                import traci
                traci.vehicle.setColor(taxi_id, (0, 255, 0, 255)) # 绿色
            except:
                pass
