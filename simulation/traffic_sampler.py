import traci
from database.db_manager import DBManager

class TrafficSampler:
    """采集 SUMO 实时路网状态并保存快照，支持时间预测和拥堵感知"""
    
    def __init__(self, db: DBManager, sample_interval=30):
        self.db = db
        self.sample_interval = sample_interval
        self.last_sample_step = -1
        self._edge_speeds = {}

    def sample(self, current_step):
        """定期采样路网速度并写入快照"""
        if current_step - self.last_sample_step < self.sample_interval:
            return
            
        self.last_sample_step = current_step
        
        try:
            edge_ids = traci.edge.getIDList()
            rows = []
            
            for edge_id in edge_ids:
                if edge_id.startswith(":"):
                    continue # 忽略内部边
                    
                # 获取该路段当前的平均车速
                mean_speed = traci.edge.getLastStepMeanSpeed(edge_id)
                
                # 获取路段的最大限速 (对于 edge，通常可以取其第一条车道的限速)
                try:
                    max_speed = traci.lane.getMaxSpeed(edge_id + "_0")
                except:
                    max_speed = 13.89 # 默认 50km/h
                
                # 计算拥堵等级 (0: 畅通, 1: 轻度, 2: 严重)
                congestion_level = 0
                if max_speed > 0:
                    speed_ratio = mean_speed / max_speed
                    if speed_ratio < 0.3:
                        congestion_level = 2
                    elif speed_ratio < 0.6:
                        congestion_level = 1
                
                self._edge_speeds[edge_id] = (mean_speed, congestion_level)
                
                # 可选：将快照写入数据库，用于历史分析或离线评测
                rows.append((current_step, edge_id, mean_speed, congestion_level))
                
            if rows:
                self.db.cursor.executemany(
                    "INSERT OR REPLACE INTO traffic_state (step, edge_id, speed, congestion_level) VALUES (?, ?, ?, ?)",
                    rows
                )
                self.db.commit()
                
        except Exception as e:
            print(f"Error sampling traffic: {e}")

    def get_edge_speed(self, edge_id):
        """获取某条边的实时速度和拥堵等级"""
        return self._edge_speeds.get(edge_id, (None, 0))

    def get_free_edges(self, fallback_edges):
        """获取当前完全畅通 (congestion_level == 0) 的道路列表，如果没有则返回 fallback_edges"""
        free_edges = [edge_id for edge_id, (_, congestion) in self._edge_speeds.items() if congestion == 0]
        if not free_edges:
            return fallback_edges
        return free_edges
