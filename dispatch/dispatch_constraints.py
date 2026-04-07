class DispatchConstraints:
    """派单限制规则管控"""
    MAX_PHYSICAL_DISTANCE_SQ = 1000000 # 缩短接驾距离：1000米平方 (原为1500米)
    MAX_ROUTE_EDGES = 25               # 缩短最大绕行边数：最多绕行25条边 (原为30)

    @classmethod
    def is_within_physical_limit(cls, tx, ty, ox, oy):
        """是否在物理距离限制内"""
        dist_sq = (tx - ox)**2 + (ty - oy)**2
        return dist_sq <= cls.MAX_PHYSICAL_DISTANCE_SQ

    @classmethod
    def is_within_route_limit(cls, route_len):
        """是否在导航距离限制内"""
        return 1 <= route_len < cls.MAX_ROUTE_EDGES
