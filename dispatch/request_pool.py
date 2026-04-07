from database.db_manager import DBManager

class RequestPool:
    """管理 PENDING 状态的订单池及超时控制"""
    def __init__(self, db: DBManager, timeout_steps=600):
        self.db = db
        self.timeout_steps = timeout_steps

    def get_pending_requests(self, current_step):
        self.db.cursor.execute(
            "SELECT request_id, origin_x, origin_y, origin_edge, dest_edge FROM trip_requests WHERE status='PENDING' AND dispatch_time <= ?",
            (current_step,)
        )
        return self.db.cursor.fetchall()

    def get_stuck_assignments(self, current_step):
        """获取接单后卡死在路上的订单"""
        # 缩短超时判定，比如卡死 300 步（5分钟）就解救出来，不要死等 10 分钟
        self.db.cursor.execute(
            """SELECT r.request_id, a.taxi_id FROM trip_requests r 
               JOIN assignments a ON r.request_id = a.request_id 
               WHERE r.status='ASSIGNED' AND a.assign_time < ?""",
            (current_step - 300,)
        )
        return self.db.cursor.fetchall()

    def get_timeout_pending_requests(self, current_step):
        """获取等待派单超时的订单"""
        self.db.cursor.execute(
            "SELECT request_id FROM trip_requests WHERE status='PENDING' AND dispatch_time < ?",
            (current_step - self.timeout_steps,)
        )
        return self.db.cursor.fetchall()

    def cancel_timeout_requests(self, current_step):
        """取消超时 PENDING 的订单"""
        self.db.cursor.execute(
            "UPDATE trip_requests SET status='CANCELLED' WHERE status='PENDING' AND dispatch_time < ?",
            (current_step - self.timeout_steps,)
        )
