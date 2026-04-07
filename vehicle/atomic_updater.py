from vehicle.state_machine import StateMachine

class AtomicUpdater:
    """提供数据库级别的原子操作，防止并发派单冲突"""
    
    @staticmethod
    def assign_vehicle(db, taxi_id, request_id, assign_time):
        """原子分配车辆接单 (IDLE -> PICKUP)"""
        db.begin_transaction()
        try:
            # 乐观锁：先检查状态
            db.cursor.execute("SELECT status FROM taxis WHERE taxi_id=?", (taxi_id,))
            row = db.cursor.fetchone()
            if not row or not StateMachine.is_available_for_dispatch(row[0]):
                db.rollback()
                return False

            # 更新车辆和请求状态
            db.cursor.execute("UPDATE taxis SET status='PICKUP' WHERE taxi_id=?", (taxi_id,))
            db.cursor.execute("UPDATE trip_requests SET status='ASSIGNED' WHERE request_id=?", (request_id,))
            db.cursor.execute("INSERT INTO assignments (request_id, taxi_id, assign_time) VALUES (?,?,?)",
                                (request_id, taxi_id, assign_time))
            db.commit()
            return True
        except Exception:
            db.rollback()
            return False

    @staticmethod
    def start_rebalance(db, taxi_id, from_cell, to_cell, current_step):
        """原子标记车辆开始重平衡 (IDLE -> REBALANCING)"""
        db.begin_transaction()
        try:
            db.cursor.execute("SELECT status FROM taxis WHERE taxi_id=?", (taxi_id,))
            row = db.cursor.fetchone()
            if not row or not StateMachine.is_available_for_rebalance(row[0]):
                db.rollback()
                return False

            db.cursor.execute("UPDATE taxis SET status='REBALANCING' WHERE taxi_id=?", (taxi_id,))
            db.cursor.execute("""
                INSERT INTO rebalance_logs (step, taxi_id, from_cell, to_cell, dispatch_time)
                VALUES (?, ?, ?, ?, ?)
            """, (current_step, taxi_id, from_cell, to_cell, current_step))
            db.commit()
            return True
        except Exception:
            db.rollback()
            return False

    @staticmethod
    def reset_to_idle(db, taxi_id):
        """原子重置车辆为 IDLE"""
        try:
            db.cursor.execute("UPDATE taxis SET status='IDLE' WHERE taxi_id=?", (taxi_id,))
            db.commit()
            return True
        except Exception:
            db.rollback()
            return False
