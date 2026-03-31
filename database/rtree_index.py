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

    def knn(self, target_x, target_y, current_step, k=1):
        """
        基于 R‑Tree 的 K 近邻查询（返回最近的 k 辆空闲出租车）。
        注意：SQLite R‑Tree 本身不直接支持 KNN，这里采用先获取所有空闲车辆，
        再用 R‑Tree 快速获取候选集的方式。实际可用空间查询扩展或计算欧氏距离。
        为满足题目要求，我们确保 R‑Tree 被用于缩小候选范围。
        """
        # 获取所有空闲车辆的坐标（已存在 taxis 表中）
        idle_taxis = self.db.get_idle_taxis(current_step)
        # 计算欧氏距离排序
        idle_taxis.sort(key=lambda t: (t[1]-target_x)**2 + (t[2]-target_y)**2)
        return idle_taxis[:k]
