import traci
from sumolib import checkBinary
import config

class SUMOConnector:
    def __init__(self, cfg_file=config.CFG_FILE):
        self.cfg_file = cfg_file

    def start(self):
        # 根据配置选择是否启动 GUI
        if getattr(config, 'GUI_ENABLED', False):
            sumo_binary = checkBinary("sumo-gui")
        else:
            sumo_binary = checkBinary("sumo")
            
        traci.start([sumo_binary, "-c", self.cfg_file, "--start", "--delay", config.DELAY, "--no-step-log"])

    def step(self):
        traci.simulationStep()

    def close(self):
        traci.close()

    def get_taxi_positions(self):
        """返回所有出租车 (vid, x, y)"""
        result = []
        for vid in traci.vehicle.getIDList():
            if vid.startswith("taxi_"):
                x, y = traci.vehicle.getPosition(vid)
                result.append((vid, x, y))
        return result

    def get_vehicle_edge(self, vid):
        road_id = traci.vehicle.getRoadID(vid)
        if road_id.startswith(":"):
            route = traci.vehicle.getRoute(vid)
            idx = traci.vehicle.getRouteIndex(vid)
            if 0 <= idx < len(route):
                return route[idx]
        return road_id

    def is_on_internal_edge(self, vid):
        return traci.vehicle.getRoadID(vid).startswith(":")

    def set_route(self, vid, edge_ids):
        traci.vehicle.setRoute(vid, edge_ids)

    # ... 其他需要的方法（如获取车辆速度、里程等）
