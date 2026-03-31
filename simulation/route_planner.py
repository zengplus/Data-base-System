import sumolib
import config

class RoutePlanner:
    def __init__(self, net_file=config.NET_FILE):
        self.net = sumolib.net.readNet(net_file)

    def get_shortest_path(self, start_edge_id, end_edge_id):
        start_edge = self.net.getEdge(start_edge_id)
        end_edge = self.net.getEdge(end_edge_id)
        path, _ = self.net.getShortestPath(start_edge, end_edge)
        return [e.getID() for e in path] if path else [start_edge_id]
