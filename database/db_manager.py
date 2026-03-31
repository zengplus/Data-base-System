import sqlite3
import config

class DBManager:
    def __init__(self, db_path=config.DB_FILE):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.init_tables()

    def init_tables(self):
        """根据 SQL_FILE 创建表（需先定义好所有表结构）"""
        with open(config.SQL_FILE, 'r') as f:
            self.cursor.executescript(f.read())
        self.conn.commit()

    def begin_transaction(self):
        self.cursor.execute("BEGIN TRANSACTION")

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()

    # 其他常用方法：插入/更新/查询，可进一步封装
    def update_taxi_location(self, taxi_id, x, y, step):
        """更新 taxi 表位置并返回 R‑Tree 更新所需的数据"""
        self.cursor.execute("""
            UPDATE taxis SET current_x=?, current_y=?, last_update=?
            WHERE taxi_id=?
        """, (x, y, step, taxi_id))

    def update_taxi_status(self, taxi_id, new_status):
        self.cursor.execute("UPDATE taxis SET status=? WHERE taxi_id=?", (new_status, taxi_id))

    def get_idle_taxis(self, current_step):
        """返回空闲出租车列表 (taxi_id, x, y)
        注意：允许获取最近几个 step 更新过的车辆，避免因为某个 step 没有位置更新导致车辆不可用
        """
        self.cursor.execute("SELECT taxi_id, current_x, current_y FROM taxis WHERE status='IDLE' AND last_update >= ?", (current_step - 2,))
        return self.cursor.fetchall()

    def assign_vehicle(self, taxi_id, request_id, assign_time):
        """原子分配车辆：更新出租车状态、请求状态、记录分配表"""
        self.begin_transaction()
        try:
            self.cursor.execute("UPDATE taxis SET status='PICKUP' WHERE taxi_id=?", (taxi_id,))
            self.cursor.execute("UPDATE trip_requests SET status='ASSIGNED' WHERE request_id=?", (request_id,))
            self.cursor.execute("INSERT INTO assignments (request_id, taxi_id, assign_time) VALUES (?,?,?)",
                                (request_id, taxi_id, assign_time))
            self.commit()
            return True
        except Exception:
            self.rollback()
            return False
