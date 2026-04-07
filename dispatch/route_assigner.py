from simulation.sumo_connector import SUMOConnector

class RouteAssigner:
    """统一下发导航路线给车辆"""
    def __init__(self, sumo: SUMOConnector):
        self.sumo = sumo

    def assign_route(self, taxi_id, route):
        if route and len(route) >= 1:
            try:
                self.sumo.set_route(taxi_id, route)
                return True
            except Exception as e:
                print(f"Error setting route for {taxi_id}: {e}")
        return False
