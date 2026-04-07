from dispatch.dispatch_constraints import DispatchConstraints
from dispatch.knn_finder import KNNFinder
from simulation.sumo_connector import SUMOConnector
from simulation.route_planner import RoutePlanner

class DispatchAssigner:
    """多目标派单决策与最优车辆筛选 (V0.2)"""
    def __init__(self, sumo: SUMOConnector, route_planner: RoutePlanner, traffic_sampler):
        self.sumo = sumo
        self.route_planner = route_planner
        self.traffic_sampler = traffic_sampler

    def _estimate_travel_time(self, route):
        """V0.2 优化：基于实时拥堵和真实路网长度评估行驶时间"""
        if not route:
            return float('inf')
        total_time = 0
        import traci
        for edge_id in route:
            speed, congestion = self.traffic_sampler.get_edge_speed(edge_id)
            
            # 获取路段长度，如果没有缓存则使用默认值
            try:
                length = traci.lane.getLength(edge_id + "_0")
            except:
                length = 100.0 # 默认 100 米
                
            # 如果 speed 无效或太小，给一个保底速度避免除零
            if speed is None or speed < 1.0:
                speed = 5.0 # 默认保底速度 5 m/s
                
            # 基础行驶时间 = 长度 / 速度
            base_time = length / speed
            
            # 加上拥堵带来的额外惩罚时间 (模拟红绿灯排队和走走停停)
            # 这里加大惩罚力度，让拥堵路线的成本显著高于畅通路线
            penalty = 0.0
            if congestion == 2:
                penalty = 120.0 # 严重拥堵，相当于等了两个长红绿灯
            elif congestion == 1:
                penalty = 40.0  # 轻度拥堵
                
            total_time += (base_time + penalty)
            
        return total_time

    def find_best_taxi(self, idle_taxis, ox, oy, origin_edge):
        """寻找综合时间成本最低的出租车"""
        best_taxi_id = None
        best_route = None
        
        # 1. 先尝试找同边车辆 (Time = 0)
        for taxi in idle_taxis:
            taxi_id = taxi[0]
            try:
                if not self.sumo.is_on_internal_edge(taxi_id):
                    current_edge = self.sumo.get_vehicle_edge(taxi_id)
                    if current_edge == origin_edge:
                        return taxi_id, [current_edge]
            except Exception:
                continue

        # 2. 寻找真实行驶时间最短的车辆
        min_travel_time = float('inf')
        
        for taxi in idle_taxis:
            taxi_id, tx, ty, cell_id = taxi
            
            if not DispatchConstraints.is_within_physical_limit(tx, ty, ox, oy):
                continue

            try:
                if not self.sumo.is_on_internal_edge(taxi_id):
                    current_edge = self.sumo.get_vehicle_edge(taxi_id)
                    route = self.route_planner.get_shortest_path(current_edge, origin_edge)
                    
                    if DispatchConstraints.is_within_route_limit(len(route)):
                        # V0.2: 使用路网时间评估而非仅仅看路段数量
                        travel_time = self._estimate_travel_time(route)
                        if travel_time < min_travel_time:
                            min_travel_time = travel_time
                            best_taxi_id = taxi_id
                            best_route = route
            except Exception:
                continue
                
        return best_taxi_id, best_route
