from database.db_manager import DBManager
import config
import math

class RequestValidator:
    """订单合法性与物理连通性校验"""
    
    @staticmethod
    def is_valid_trip(route_planner, origin_edge, dest_edge, ox, oy, cx, cy):
        """校验行程是否符合距离要求，并且在路网上可达"""
        trip_dist = math.sqrt((cx - ox)**2 + (cy - oy)**2)
        # 将最大订单距离从 1500米 缩短至 800米，加快订单周转率
        if 200 <= trip_dist <= 800:
            route = route_planner.get_shortest_path(origin_edge, dest_edge)
            if len(route) >= 1:
                return True
        return False

    @staticmethod
    def get_fallback_dest(route_planner, edges, origin_edge):
        """如果原终点不可达，随机寻找一个可达终点"""
        import random
        for _ in range(50):
            candidate = random.choice(edges)
            route = route_planner.get_shortest_path(origin_edge.getID(), candidate.getID())
            if len(route) >= 1:
                return candidate
        return origin_edge # 极端情况原地不动
