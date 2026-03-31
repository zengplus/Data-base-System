from database.db_manager import DBManager
from simulation.sumo_connector import SUMOConnector
from simulation.route_planner import RoutePlanner
import config
import math

class Rebalancer:
    def __init__(self, db: DBManager, sumo: SUMOConnector, route_planner: RoutePlanner, net):
        self.db = db
        self.sumo = sumo
        self.route_planner = route_planner
        self.net = net
        self.last_rebalance_step = 0

        # 计算路网边界
        self.x_min, self.x_max, self.y_min, self.y_max = self._get_network_bounds()
        self.cell_width = (self.x_max - self.x_min) / config.GRID_SIZE
        self.cell_height = (self.y_max - self.y_min) / config.GRID_SIZE

    def _get_network_bounds(self):
        """获取路网坐标范围"""
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
        """返回坐标所在的网格索引 (i, j)"""
        i = int((x - self.x_min) / self.cell_width)
        j = int((y - self.y_min) / self.cell_height)
        i = max(0, min(i, config.GRID_SIZE-1))
        j = max(0, min(j, config.GRID_SIZE-1))
        return i, j

    def compute_supply_demand(self, current_step):
        """计算每个网格的出租车供给与需求"""
        # 供给：当前空闲出租车数量（按位置划分）
        idle_taxis = self.db.get_idle_taxis(current_step)
        supply = [[0]*config.GRID_SIZE for _ in range(config.GRID_SIZE)]
        for _, x, y in idle_taxis:
            i, j = self._get_cell(x, y)
            supply[i][j] += 1

        # 需求：过去一段时间内的请求数量（例如最近 5 分钟）
        lookback = 300  # 5分钟
        self.db.cursor.execute("""
            SELECT origin_x, origin_y FROM trip_requests
            WHERE dispatch_time > ? AND status != 'PENDING'
        """, (current_step - lookback,))
        requests = self.db.cursor.fetchall()
        demand = [[0]*config.GRID_SIZE for _ in range(config.GRID_SIZE)]
        for ox, oy in requests:
            i, j = self._get_cell(ox, oy)
            demand[i][j] += 1

        return supply, demand

    def rebalance(self, current_step):
        """执行重平衡：找出需求大于供给的区域，调度空闲车辆前往"""
        if current_step - self.last_rebalance_step < config.REBALANCE_INTERVAL:
            return
        self.last_rebalance_step = current_step

        supply, demand = self.compute_supply_demand(current_step)
        # 找出需要增加出租车的区域（需求 > 供给 且 需求 > 阈值）
        threshold = 5  # 最少需求数量
        target_cells = []
        for i in range(config.GRID_SIZE):
            for j in range(config.GRID_SIZE):
                if demand[i][j] > supply[i][j] and demand[i][j] > threshold:
                    target_cells.append((i, j))

        if not target_cells:
            return

        # 对于每个目标区域，从供给富裕的区域调度一辆空闲出租车
        # 简单策略：依次处理，寻找最近的有空余车辆的区域
        # 实际可优化：全局匹配
        for ti, tj in target_cells:
            # 计算目标区域的中心坐标
            center_x = self.x_min + (ti + 0.5) * self.cell_width
            center_y = self.y_min + (tj + 0.5) * self.cell_height

            # 寻找距离该中心最近的空闲出租车（从供给大于需求的区域找）
            best_taxi = None
            best_dist = float('inf')
            for taxi_id, x, y in self.db.get_idle_taxis(current_step):
                try:
                    if self.sumo.is_on_internal_edge(taxi_id):
                        continue
                except Exception:
                    # 车辆可能因为碰撞被移除，或者不在路网上
                    continue
                # 避免从目标区域本身取车（可选）
                dist = (x - center_x)**2 + (y - center_y)**2
                if dist < best_dist:
                    best_dist = dist
                    best_taxi = taxi_id

            if best_taxi:
                # 将出租车调度到目标区域中心
                # 需要找到最近的边作为目的地
                # 简化：找到距离中心最近的边
                nearest_edge = None
                min_edge_dist = float('inf')
                for edge in self.net.getEdges():
                    shape = edge.getShape()
                    if shape:
                        for ex, ey in shape:
                            d = (ex - center_x)**2 + (ey - center_y)**2
                            if d < min_edge_dist:
                                min_edge_dist = d
                                nearest_edge = edge.getID()
                if nearest_edge:
                    current_edge = self.sumo.get_vehicle_edge(best_taxi)
                    route = self.route_planner.get_shortest_path(current_edge, nearest_edge)
                    self.sumo.set_route(best_taxi, route)
                    # 可选：标记车辆状态为 REBALANCING，防止被分配
                    # self.db.update_taxi_status(best_taxi, 'REBALANCING')
                    # 并设定一个定时器，到达后恢复 IDLE（此处简化，不做）
