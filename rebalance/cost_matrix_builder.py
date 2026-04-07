from database.spatial_cache import SpatialCache

class CostMatrixBuilder:
    """构建区域间的时间成本矩阵"""
    def __init__(self, travel_time_predictor):
        self.predictor = travel_time_predictor
        self.spatial_cache = SpatialCache()

    def build(self, source_regions, target_regions, db=None):
        """
        source_regions: 盈余区域列表 (供大于求)
        target_regions: 赤字区域列表 (需大于求)
        返回: 成本矩阵字典 {(src, dst): time}
        """
        matrix = {}
        for src in source_regions:
            src_edge = self.spatial_cache.get_central_edge(src)
            if not src_edge and db:
                try:
                    src_edge = db.cursor.execute("SELECT origin_edge FROM trip_requests WHERE cell_id=? LIMIT 1", (src,)).fetchone()
                    if src_edge: src_edge = src_edge[0]
                except: pass
                
            for dst in target_regions:
                dst_edge = self.spatial_cache.get_central_edge(dst)
                if not dst_edge and db:
                    try:
                        dst_edge = db.cursor.execute("SELECT origin_edge FROM trip_requests WHERE cell_id=? LIMIT 1", (dst,)).fetchone()
                        if dst_edge: dst_edge = dst_edge[0]
                    except: pass
                    
                time_cost = self.predictor.predict(src_edge, dst_edge)
                matrix[(src, dst)] = time_cost
        return matrix
