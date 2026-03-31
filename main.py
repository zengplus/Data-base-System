import config
from database.db_manager import DBManager
from database.rtree_index import RTreeIndex
from simulation.sumo_connector import SUMOConnector
from simulation.route_planner import RoutePlanner
from dispatch.request_handler import generate_requests
from dispatch.scheduler import Scheduler
from rebalance.rebalancer import Rebalancer
import sumolib
import os

def main():
    # 1. 初始化数据库
    db = DBManager()
    
    # 2. 初始化路网规划器
    net = sumolib.net.readNet(config.NET_FILE)
    route_planner = RoutePlanner(config.NET_FILE)
    
    # 3. 生成随机请求（仅第一次，如果数据库为空）
    # 你可以先检查表是否为空再决定是否生成
    db.cursor.execute("SELECT COUNT(*) FROM trip_requests")
    if db.cursor.fetchone()[0] == 0:
        generate_requests(db, route_planner, net)

    # 4. 启动 SUMO 仿真
    sumo = SUMOConnector(cfg_file=config.CFG_FILE)
    sumo.start()

    # 5. 初始化 R‑Tree 索引（清空旧数据）
    rtree = RTreeIndex(db)
    
    # 6. 初始化调度器
    scheduler = Scheduler(db, rtree, sumo, route_planner)
    
    # 7. 初始化重平衡器
    rebalancer = Rebalancer(db, sumo, route_planner, net)

    # 8. 主循环
    seen_taxis = set()
    all_edges = net.getEdges()
    # 过滤掉内部边（以 ":" 开头的边）
    edge_ids = [e.getID() for e in all_edges if not e.getID().startswith(":")]
    
    for step in range(config.STEPS):
        try:
            sumo.step()
        except Exception as e:
            print(f"SUMO 仿真在 step {step} 遇到连接断开或异常: {e}")
            break

        # 核心：提前续接路线，防止空闲车辆到达终点被 SUMO 自动删除
        import traci
        import random
        try:
            all_vehicles = traci.vehicle.getIDList()
            for vid in all_vehicles:
                if vid.startswith("bg_") or vid.startswith("taxi_"):
                    # 检查是否是空闲状态
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
                                end_edge = random.choice(edge_ids)
                                new_path = route_planner.get_shortest_path(current_edge, end_edge)
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
                            start_edge = random.choice(edge_ids)
                            end_edge = random.choice(edge_ids)
                            route = route_planner.get_shortest_path(start_edge, end_edge)
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
                    traci.vehicle.setColor(taxi_id, (0, 255, 0, 255)) # 初始空闲状态绿色
                except Exception:
                    pass
                seen_taxis.add(taxi_id)

            # 确保车辆在数据库中（如果是新出现的车辆，插入初始状态）
            db.cursor.execute("INSERT OR IGNORE INTO taxis (taxi_id, status, current_x, current_y, last_update) VALUES (?, 'IDLE', ?, ?, ?)",
                              (taxi_id, x, y, step))
            # 更新最新位置和时间戳
            db.update_taxi_location(taxi_id, x, y, step)
            rtree.update(taxi_id, x, y)
        db.commit()

        # 处理新产生的乘客请求
        scheduler.process_pending_requests(step)

        # 检查车辆到达事件
        for taxi_id, _, _ in taxi_positions:
            if not sumo.is_on_internal_edge(taxi_id):
                current_edge = sumo.get_vehicle_edge(taxi_id)
                scheduler.handle_arrival(taxi_id, current_edge, step)

        # 定期执行重平衡
        rebalancer.rebalance(step)

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
