import json
import os
import geopandas as gpd
from shapely.geometry import Point
from database.db_manager import DBManager
from simulation.sumo_connector import SUMOConnector
from simulation.route_planner import RoutePlanner
import config

class RegionProjector:
    """参考 taxi-sim 仓库的区域划分逻辑，使用 shapefile 将坐标映射到不规则多边形区域"""
    def __init__(self):
        shp_path = os.path.join(config.BASE_DIR, 'data', 'taxi_zones', 'taxi_zones.shp')
        if os.path.exists(shp_path):
            self._gdf = gpd.read_file(shp_path)
            self._gdf = self._gdf.to_crs('EPSG:4326')
            self.use_shp = True
        else:
            self.use_shp = False
            print(f"Warning: Shapefile not found at {shp_path}. Falling back to grid zoning.")
            self._init_grid()

        self._resultCache = {}

    def _init_grid(self):
        # 如果没有 shapefile，退化为简单的网格划分
        self.grid_size = config.GRID_SIZE
        # 假设这里外部会传入边界，为了简单，退化模式在 Rebalancer 中处理
        pass

    def in_which_region(self, x, y):
        if not self.use_shp:
            return None # 让 Rebalancer 使用默认的 grid 逻辑
            
        if (x, y) in self._resultCache:
            return self._resultCache[(x,y)]
            
        # 注意：实际使用中，如果 x,y 是 SUMO 坐标，需要先转换为经纬度 (lon, lat)
        # 这里假设传入的 x, y 已经是兼容的坐标系
        series = self._gdf.contains(Point(x, y))
        inRegions = series[series == True]
        if len(inRegions) > 0:
            result = inRegions.index[0] + 1
            self._resultCache[(x,y)] = result
            return result   
        else:
            return None

class Rebalancer:
    def __init__(self, db: DBManager, sumo: SUMOConnector, route_planner: RoutePlanner, net):
        self.db = db
        self.sumo = sumo
        self.route_planner = route_planner
        self.net = net
        self.last_rebalance_step = 0
        
        self.region_projector = RegionProjector()

        # 预加载中心边映射 (参考 taxi-sim)
        self.central_edges = {}
        json_path = os.path.join(config.BASE_DIR, 'data', 'pre_cal', 'centralEdges.json')
        if os.path.exists(json_path):
            with open(json_path, 'r') as f:
                raw_data = json.load(f)
                for k, v in raw_data.items():
                    self.central_edges[int(k)] = str(v)
        else:
            print(f"Warning: centralEdges.json not found at {json_path}.")

        # 计算路网边界 (作为网格退化方案)
        self.x_min, self.x_max, self.y_min, self.y_max = self._get_network_bounds()
        self.cell_width = (self.x_max - self.x_min) / config.GRID_SIZE
        self.cell_height = (self.y_max - self.y_min) / config.GRID_SIZE

    def _get_network_bounds(self):
        edges = self.net.getEdges()
        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')
        for e in edges:
            shape = e.getShape()
            for x, y in shape:
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)
        return min_x, max_x, min_y, max_y

    def _get_cell(self, x, y):
        """网格退化方案的坐标映射"""
        i = int((x - self.x_min) / self.cell_width)
        j = int((y - self.y_min) / self.cell_height)
        i = max(0, min(config.GRID_SIZE - 1, i))
        j = max(0, min(config.GRID_SIZE - 1, j))
        return i, j

    def get_region_id(self, x, y):
        """获取坐标所在的区域 ID (优先使用 Shapefile，退化为 Grid ID)"""
        region_id = self.region_projector.in_which_region(x, y)
        if region_id is not None:
            return str(region_id)
        # 退化为 Grid 字符串 ID，例如 "2_3"
        i, j = self._get_cell(x, y)
        return f"{i}_{j}"

    def compute_supply_demand(self, current_step):
        """计算每个区域的出租车供给与需求"""
        supply = {}
        demand = {}

        # 供给：当前空闲出租车数量
        idle_taxis = self.db.get_idle_taxis(current_step)
        for _, x, y in idle_taxis:
            reg = self.get_region_id(x, y)
            supply[reg] = supply.get(reg, 0) + 1

        # 需求：过去一段时间内的请求数量
        lookback = 300  # 5分钟
        self.db.cursor.execute("""
            SELECT origin_x, origin_y FROM trip_requests
            WHERE dispatch_time > ? AND status != 'PENDING'
        """, (current_step - lookback,))
        requests = self.db.cursor.fetchall()
        
        for ox, oy in requests:
            reg = self.get_region_id(ox, oy)
            demand[reg] = demand.get(reg, 0) + 1

        return supply, demand

    def rebalance(self, current_step):
        """执行重平衡：计算供需差，从富裕区域调车到短缺区域"""
        if current_step - self.last_rebalance_step < config.REBALANCE_INTERVAL:
            return
        self.last_rebalance_step = current_step

        supply, demand = self.compute_supply_demand(current_step)
        
        # 获取所有涉及的区域
        all_regions = set(supply.keys()).union(set(demand.keys()))
        
        # 供需差：demand - supply
        gap = {}
        target_regions = []  # 缺车区域 (gap > 0)
        source_regions = set() # 富裕区域 (gap < 0)
        
        for reg in all_regions:
            d = demand.get(reg, 0)
            s = supply.get(reg, 0)
            g = d - s
            gap[reg] = g
            if g > 0:
                target_regions.append({'region': reg, 'gap': g})
            elif g < 0:
                source_regions.add(reg)

        # 按缺口大小排序，优先满足最缺车的区域
        target_regions.sort(key=lambda x: x['gap'], reverse=True)

        if not target_regions or not source_regions:
            return

        # 收集富裕区域的空车列表
        source_taxis = []
        idle_taxis_list = self.db.get_idle_taxis(current_step)
        
        # 限制：只允许最多 20% 的空闲车参与 Rebalance
        max_rebalance_count = max(1, int(len(idle_taxis_list) * 0.2))
        
        for taxi_id, x, y in idle_taxis_list:
            reg = self.get_region_id(x, y)
            if reg in source_regions:
                try:
                    if not self.sumo.is_on_internal_edge(taxi_id):
                        source_taxis.append({'id': taxi_id, 'x': x, 'y': y, 'region': reg})
                except Exception:
                    pass

        # 如果可用车源超过了 20% 的限制，截断它
        if len(source_taxis) > max_rebalance_count:
            source_taxis = source_taxis[:max_rebalance_count]

        # 调度匹配
        for target in target_regions:
            reg_target = target['region']
            needed = target['gap']
            
            for _ in range(needed):
                if not source_taxis:
                    break
                
                # 寻找距离目标区域中心最近的空车
                # 为了简单，如果使用网格，我们计算网格中心；如果是不规则区域，用 centralEdges
                target_edge = None
                center_x, center_y = 0, 0
                
                # 如果是数字区域ID且存在于 centralEdges 中
                if reg_target.isdigit() and int(reg_target) in self.central_edges:
                    target_edge = self.central_edges[int(reg_target)]
                    # 近似取第一条边的中心作为距离计算基准
                    try:
                        shape = self.net.getEdge(target_edge).getShape()
                        center_x = sum([p[0] for p in shape]) / len(shape)
                        center_y = sum([p[1] for p in shape]) / len(shape)
                    except:
                        pass
                else:
                    # 退化逻辑：找到目标网格内的任意一条边
                    if "_" in reg_target:
                        ti, tj = map(int, reg_target.split("_"))
                        center_x = self.x_min + (ti + 0.5) * self.cell_width
                        center_y = self.y_min + (tj + 0.5) * self.cell_height
                        
                        min_edge_dist = float('inf')
                        for edge in self.net.getEdges():
                            shape = edge.getShape()
                            if shape:
                                for ex, ey in shape:
                                    d = (ex - center_x)**2 + (ey - center_y)**2
                                    if d < min_edge_dist:
                                        min_edge_dist = d
                                        target_edge = edge.getID()

                if not target_edge:
                    continue

                # 寻找距离该目标区域最近的富裕车辆
                best_idx = -1
                best_dist = float('inf')
                for idx, taxi in enumerate(source_taxis):
                    # 如果能获取到目标区域的中心点，则计算距离
                    if center_x != 0 and center_y != 0:
                        dist = (taxi['x'] - center_x)**2 + (taxi['y'] - center_y)**2
                    else:
                        dist = 0 # 无法计算则默认
                    
                    if dist < best_dist:
                        best_dist = dist
                        best_idx = idx

                if best_idx != -1:
                    # 距离限制：如果最近的富裕车离目标区域超过 2000 米（平方大于 4000000），则放弃跨全图调度
                    if best_dist > 4000000:
                        break
                        
                    best_taxi = source_taxis.pop(best_idx)
                    taxi_id = best_taxi['id']
                    
                    try:
                        current_edge = self.sumo.get_vehicle_edge(taxi_id)
                        route = self.route_planner.get_shortest_path(current_edge, target_edge)
                        if len(route) >= 1:
                            self.sumo.set_route(taxi_id, route)
                    except Exception:
                        pass
