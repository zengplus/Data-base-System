from database.db_manager import DBManager

class SupplyDemand:
    """计算区域供需差"""
    def __init__(self, db: DBManager):
        self.db = db

    def compute(self, current_step, lookback=300):
        supply = {}
        demand = {}

        # 供给：当前空闲出租车数量
        idle_taxis = self.db.get_idle_taxis(current_step)
        for _, _, _, cell_id in idle_taxis:
            if cell_id:
                supply[cell_id] = supply.get(cell_id, 0) + 1

        # 需求：过去一段时间内的请求数量，以及当前还在等车的订单
        self.db.cursor.execute("""
            SELECT cell_id FROM trip_requests
            WHERE (dispatch_time > ? AND status != 'PENDING') 
               OR status = 'PENDING'
        """, (current_step - lookback,))
        requests = self.db.cursor.fetchall()
        
        for (cell_id,) in requests:
            if cell_id:
                demand[cell_id] = demand.get(cell_id, 0) + 1

        return supply, demand
