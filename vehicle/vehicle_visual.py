import traci

class VehicleVisual:
    """集中管理 SUMO GUI 中的车辆颜色显示"""
    
    COLORS = {
        'IDLE': (0, 255, 0, 255),          # 绿色
        'PICKUP': (255, 165, 0, 255),      # 橙色
        'OCCUPIED': (255, 0, 0, 255),      # 红色
        'REBALANCING': (0, 191, 255, 255)  # 深空蓝色 (区分于普通的空闲)
    }

    @classmethod
    def set_color(cls, taxi_id, status):
        """根据状态设置颜色"""
        if status in cls.COLORS:
            try:
                traci.vehicle.setColor(taxi_id, cls.COLORS[status])
            except Exception:
                pass # 车辆可能已不在地图上
