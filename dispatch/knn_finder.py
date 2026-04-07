from database.rtree_index import RTreeIndex

class KNNFinder:
    """基于 R-Tree 的 K 近邻查询"""
    def __init__(self, rtree: RTreeIndex):
        self.rtree = rtree

    def find_nearest_idle_taxis(self, x, y, current_step, k=15):
        """返回距离目标坐标最近的 k 辆空闲车 (taxi_id, x, y, cell_id)"""
        return self.rtree.knn(x, y, current_step, k)
