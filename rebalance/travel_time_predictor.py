class TravelTimePredictor:
    """预测含拥堵的真实行驶时间"""
    def __init__(self, traffic_sampler, route_planner):
        self.traffic_sampler = traffic_sampler
        self.route_planner = route_planner

    def predict(self, start_edge, end_edge):
        if not start_edge or not end_edge:
            return float('inf')
        
        route = self.route_planner.get_shortest_path(start_edge, end_edge)
        if not route or len(route) < 1:
            return float('inf')

        total_time = 0
        for edge_id in route:
            speed, congestion = self.traffic_sampler.get_edge_speed(edge_id)
            # 简化版时间计算，真实应用中应使用 edge length / speed
            penalty = 1.0
            if congestion == 2:
                penalty = 5.0
            elif congestion == 1:
                penalty = 2.0
            total_time += penalty
            
        return total_time
