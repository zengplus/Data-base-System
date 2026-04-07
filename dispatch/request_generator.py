import random
import math
from database.db_manager import DBManager
from database.spatial_cache import SpatialCache
from simulation.route_planner import RoutePlanner
from dispatch.request_validator import RequestValidator
import config

class RequestGenerator:
    """处理订单的随机生成及时空分布规则"""
    
    def __init__(self, db: DBManager, route_planner: RoutePlanner, net):
        self.db = db
        self.route_planner = route_planner
        self.net = net
        self.spatial_cache = SpatialCache()

    def generate(self):
        edges = [e for e in self.net.getEdges() if not e.isSpecial()]
        edge_centers = {}
        
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

        edge_distances = []
        for e in edges:
            cx, cy = edge_centers[e.getID()]
            dist = math.sqrt((cx - network_center_x)**2 + (cy - network_center_y)**2)
            edge_distances.append((e, dist))

        # 获取宏观 3 区域的边界判定半径 (四分之一宽度为半径)
        radius_sq = ((max_x - min_x) * 0.25) ** 2

        rows = []
        for i in range(config.REQUEST_COUNT):
            time_fraction = math.pow(random.random(), 1.5) 
            dispatch_time = int(time_fraction * (config.SIM_END - 1))
            if i < 5:
                dispatch_time = random.randint(0, 10)
            
            # 制造极端的“中心热点”潮汐现象
            # 80% 的订单强制生成在 Center 区，20% 在外围
            is_center_demand = random.random() < 0.8
            
            weights = []
            for e, dist in edge_distances:
                if is_center_demand:
                    # 只有距离中心的平方 <= radius_sq 的边才有权重
                    weight = 1.0 if dist**2 <= radius_sq else 0.0
                else:
                    # 外围订单
                    weight = 1.0 if dist**2 > radius_sq else 0.0
                weights.append(weight)
                
            # 如果某次随机构建权重全为0（极端情况），回退到均匀分布
            if sum(weights) == 0:
                weights = [1.0] * len(edges)
                
            origin_edge = random.choices(edges, weights=weights, k=1)[0]
            ox, oy = edge_centers[origin_edge.getID()]
            
            dest_edge = None
            attempts = 0
            while dest_edge is None and attempts < 100:
                candidate = random.choice(edges)
                if candidate.getID() != origin_edge.getID():
                    cx, cy = edge_centers[candidate.getID()]
                    if RequestValidator.is_valid_trip(self.route_planner, origin_edge.getID(), candidate.getID(), ox, oy, cx, cy):
                        dest_edge = candidate
                attempts += 1
                
            if dest_edge is None:
                dest_edge = RequestValidator.get_fallback_dest(self.route_planner, edges, origin_edge)

            dx, dy = edge_centers[dest_edge.getID()]
            
            # V0.2 新增：记录订单所在网格/区域
            cell_id = self.spatial_cache.get_region_id(ox, oy)
            
            rows.append((
                dispatch_time, origin_edge.getID(), dest_edge.getID(),
                ox, oy, dx, dy, 'PENDING', cell_id
            ))

        self.db.cursor.executemany(
            "INSERT INTO trip_requests (dispatch_time, origin_edge, dest_edge, origin_x, origin_y, dest_x, dest_y, status, cell_id) VALUES (?,?,?,?,?,?,?,?,?)",
            rows
        )
        self.db.commit()
