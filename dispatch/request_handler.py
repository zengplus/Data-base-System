import random
import math
from database.db_manager import DBManager
from simulation.route_planner import RoutePlanner
import config
import traci

def generate_requests(db: DBManager, route_planner: RoutePlanner, net):
    """生成具有时空动态特性的 REQUEST_COUNT 个订单请求"""
    # 获取所有非特殊边及其中心坐标
    edges = [e for e in net.getEdges() if not e.isSpecial()]
    edge_centers = {}
    
    # 找到整个路网的中心点（用于空间聚拢）
    min_x = min_y = float('inf')
    max_x = max_y = float('-inf')

    for e in edges:
        shape = e.getShape()
        if shape:
            xs, ys = zip(*shape)
            cx = sum(xs)/len(xs)
            cy = sum(ys)/len(ys)
        else:
            cx, cy = e.getBoundingBox()[:2]
        edge_centers[e.getID()] = (cx, cy)
        min_x, min_y = min(min_x, cx), min(min_y, cy)
        max_x, max_y = max(max_x, cx), max(max_y, cy)

    network_center_x = (min_x + max_x) / 2
    network_center_y = (min_y + max_y) / 2
    max_dist = math.sqrt((max_x - network_center_x)**2 + (max_y - network_center_y)**2)

    # 计算所有边到中心的距离，用于后续的概率计算
    edge_distances = []
    for e in edges:
        cx, cy = edge_centers[e.getID()]
        dist = math.sqrt((cx - network_center_x)**2 + (cy - network_center_y)**2)
        edge_distances.append((e, dist))

    rows = []
    for i in range(config.REQUEST_COUNT):
        # 1. 时间动态生成：越往后订单越多（使用幂函数实现缓慢增长）
        # 改为使用 1.5 次方，让一开始就有订单，但后期更密集
        # time_fraction 在 0 到 1 之间
        time_fraction = math.pow(random.random(), 1.5) 
        # 将 dispatch_time 均匀分布到整个仿真周期 (0 到 SIM_END)
        dispatch_time = int(time_fraction * (config.SIM_END - 1))
        
        # 确保一开始（第 0~10 步）一定有几个种子订单
        if i < 5:
            dispatch_time = random.randint(0, 10)
        
        # 2. 空间动态聚拢：随着时间推移，订单越来越向中心靠拢
        # time_fraction 越接近 1（后期），权重中对距离的惩罚越大
        clustering_factor = time_fraction * 5.0 # 聚拢系数，后期最高为5
        
        # 为每条边计算被选为起点的概率权重
        weights = []
        for e, dist in edge_distances:
            # normalized_dist 在 0~1 之间
            normalized_dist = dist / (max_dist + 1e-6)
            # 距离越远，权重越低，且时间越靠后，降低的幅度越大
            weight = math.exp(-clustering_factor * normalized_dist)
            weights.append(weight)
            
        # 根据计算出的权重随机选择起点
        origin_edge = random.choices(edges, weights=weights, k=1)[0]
        
        # 3. 距离与连通性限制：终点不能离起点太远，且必须有一条合法的路径
        # 限制行程直线距离在 300 到 1500 米之间
        ox, oy = edge_centers[origin_edge.getID()]
        dest_edge = None
        attempts = 0
        while dest_edge is None and attempts < 100:
            candidate = random.choice(edges)
            if candidate.getID() != origin_edge.getID():
                cx, cy = edge_centers[candidate.getID()]
                trip_dist = math.sqrt((cx - ox)**2 + (cy - oy)**2)
                if 300 <= trip_dist <= 1500:
                    # 加入物理连通性验证：确保从起点到终点在路网上是真的能开过去的！
                    route = route_planner.get_shortest_path(origin_edge.getID(), candidate.getID())
                    if len(route) >= 1:
                        dest_edge = candidate
            attempts += 1
            
        # 如果找了 100 次都没找到合适的，说明这个起点可能是在死胡同里
        if dest_edge is None:
            # 放弃这个坏起点，重新选一个（不严格符合权重，但保证可达性）
            dest_edge = origin_edge
            while dest_edge.getID() == origin_edge.getID():
                origin_edge = random.choice(edges)
                dest_edge = random.choice(edges)
                route = route_planner.get_shortest_path(origin_edge.getID(), dest_edge.getID())
                if len(route) < 1:
                    dest_edge = origin_edge # 继续循环

        ox, oy = edge_centers[origin_edge.getID()]
        dx, dy = edge_centers[dest_edge.getID()]
        rows.append((
            dispatch_time, origin_edge.getID(), dest_edge.getID(),
            ox, oy, dx, dy, 'PENDING'
        ))

    db.cursor.executemany(
        "INSERT INTO trip_requests (dispatch_time, origin_edge, dest_edge, origin_x, origin_y, dest_x, dest_y, status) VALUES (?,?,?,?,?,?,?,?)",
        rows
    )
    db.commit()

def generate_person_in_sumo(sumo, request_id, origin_edge, dest_edge, current_step):
    """在 SUMO GUI 中可视化乘客"""
    person_id = f"person_{request_id}"
    try:
        # 使用 pos=0.0 以避免超出一些短边的长度
        sumo.person.add(person_id, origin_edge, pos=0.0, depart=current_step)
        # 添加 person 的行程计划，指定等待出租车并前往目的边
        sumo.person.appendWaitingStage(person_id, duration=10000, description="waiting for taxi", stopID="")
    except Exception as e:
        print(f"Failed to add person {person_id} to SUMO: {e}")
