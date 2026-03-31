import random
from database.db_manager import DBManager
from simulation.route_planner import RoutePlanner
import config
import traci

def generate_requests(db: DBManager, route_planner: RoutePlanner, net):
    """生成 REQUEST_COUNT 个随机请求并写入 trip_requests 表"""
    # 获取所有非特殊边及其中心坐标
    edges = [e for e in net.getEdges() if not e.isSpecial()]
    edge_centers = {}
    for e in edges:
        shape = e.getShape()
        if shape:
            xs, ys = zip(*shape)
            cx = sum(xs)/len(xs)
            cy = sum(ys)/len(ys)
        else:
            cx, cy = e.getBoundingBox()[:2]
        edge_centers[e.getID()] = (cx, cy)

    rows = []
    for i in range(config.REQUEST_COUNT):
        origin_edge = random.choice(edges)
        dest_edge = random.choice(edges)
        while dest_edge.getID() == origin_edge.getID():
            dest_edge = random.choice(edges)
        dispatch_time = random.randint(0, config.SIM_END - 1)
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
