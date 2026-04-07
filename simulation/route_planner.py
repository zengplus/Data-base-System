import sumolib
import config
import heapq

class RoutePlanner:
    def __init__(self, net_file=config.NET_FILE):
        self.net = sumolib.net.readNet(net_file)
        
        # 缓存中心点，用于背景车惩罚
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
        self.center_x = (min_x + max_x) / 2
        self.center_y = (min_y + max_y) / 2
        self.radius_sq = ((max_x - min_x) * 0.25) ** 2

    def get_shortest_path(self, start_edge_id, end_edge_id, is_bg_vehicle=False):
        start_edge = self.net.getEdge(start_edge_id)
        end_edge = self.net.getEdge(end_edge_id)
        
        # 对于出租车，或者不使用背景车惩罚时，直接调用 sumolib 原生的高效 C++ 底层
        if not is_bg_vehicle:
            path, _ = self.net.getShortestPath(start_edge, end_edge)
            return [e.getID() for e in path] if path else [start_edge_id]
            
        # 对于背景车，我们使用自定义的带惩罚权重的 A* 算法，避免它们穿过市中心
        return self._custom_astar_for_bg(start_edge, end_edge)

    def _custom_astar_for_bg(self, start_edge, end_edge):
        """专门为背景车设计的 A* 算法，严厉惩罚经过市中心和单行道的路线"""
        if start_edge == end_edge:
            return [start_edge.getID()]

        def heuristic(node):
            # 简单的欧氏距离启发函数
            n_x, n_y = node.getBoundingBox()[:2]
            e_x, e_y = end_edge.getBoundingBox()[:2]
            return ((n_x - e_x)**2 + (n_y - e_y)**2) ** 0.5

        # 优先队列：(f_score, g_score, edge_id, path)
        open_set = []
        heapq.heappush(open_set, (0, 0, start_edge.getID(), [start_edge.getID()]))
        
        # 记录已访问节点及其最小代价
        g_scores = {start_edge.getID(): 0}
        
        # 防止搜索过深导致卡死，设置最大探索步数
        max_steps = 2000
        steps = 0
        
        while open_set and steps < max_steps:
            steps += 1
            _, current_g, current_edge_id, path = heapq.heappop(open_set)
            
            if current_edge_id == end_edge.getID():
                return path
                
            current_edge = self.net.getEdge(current_edge_id)
            
            # 获取所有合法的下游边 (outgoing edges)
            for out_edge in current_edge.getOutgoing():
                next_edge = out_edge.getToNode().getOutgoing()
                for next_e in next_edge:
                    next_id = next_e.getID()
                    
                    # 计算这段路的基础长度代价
                    base_cost = next_e.getLength()
                    
                    # --- 核心惩罚逻辑 ---
                    lane_num = next_e.getLaneNumber()
                    n_x, n_y = next_e.getBoundingBox()[:2]
                    dist_sq = (n_x - self.center_x)**2 + (n_y - self.center_y)**2
                    is_center = dist_sq <= self.radius_sq
                    
                    # 1. 闯入市中心惩罚
                    if is_center:
                        base_cost *= 50
                    # 2. 车道数惩罚
                    if lane_num == 1:
                        base_cost *= 20
                    elif lane_num == 2:
                        base_cost *= 5
                    elif lane_num == 3:
                        base_cost *= 2
                        
                    tentative_g = current_g + base_cost
                    
                    if next_id not in g_scores or tentative_g < g_scores[next_id]:
                        g_scores[next_id] = tentative_g
                        f_score = tentative_g + heuristic(next_e)
                        heapq.heappush(open_set, (f_score, tentative_g, next_id, path + [next_id]))
                        
        # 如果搜索失败或超时，返回单边（退化处理）
        return [start_edge.getID()]
