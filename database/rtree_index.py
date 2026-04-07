from database.db_manager import DBManager

class RTreeIndex:
    def __init__(self, db_manager: DBManager):
        self.db = db_manager

    def _get_rtree_id(self, taxi_id):
        return int(taxi_id.split('_')[1])

    def update(self, taxi_id, x, y):
        """先删除旧记录，再插入新记录（R‑Tree 更新）"""
        rtree_id = self._get_rtree_id(taxi_id)
        self.db.cursor.execute("DELETE FROM taxi_locations WHERE id=?", (rtree_id,))
        self.db.cursor.execute(
            "INSERT INTO taxi_locations(id, minX, maxX, minY, maxY) VALUES(?,?,?,?,?)",
            (rtree_id, x, x, y, y)
        )

    def knn(self, target_x, target_y, current_step, k=15):
        """
        基于 R‑Tree 的 K 近邻查询（返回最近的 k 辆空闲出租车）。
        V0.2 优化：返回更多的候选集给 dispatch_assigner，
        由其通过 Time-KNN (基于真实路网行驶时间) 进行二次筛选。
        """
        # 获取所有空闲车辆的坐标（已存在 taxis 表中）
        idle_taxis = self.db.get_idle_taxis(current_step)
        # 基础的空间距离排序（缩小搜索范围，降低路网时间计算量）
        idle_taxis.sort(key=lambda t: (t[1]-target_x)**2 + (t[2]-target_y)**2)
        return idle_taxis[:k]
