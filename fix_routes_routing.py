import sumolib
import random
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--taxis", type=int, default=300)
parser.add_argument("--bg", type=int, default=2000)
parser.add_argument("--seed", type=int, default=42)
args = parser.parse_args()

random.seed(args.seed)

net = sumolib.net.readNet('/home/shu/Documents/Data-base-System/sumo_inputs/convert-1.net.xml')
edges = net.getEdges()
edge_ids = [e.getID() for e in edges if not e.getID().startswith(':') and e.allows("passenger")]

with open("/home/shu/Documents/Data-base-System/sumo_inputs/routes.rou.xml", "w") as f:
    f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    f.write('<routes>\n')
    f.write('  <vType id="taxi" vClass="taxi" length="4.0" width="1.6" color="0,255,0" speedFactor="1.2" sigma="0.5" lcStrategic="1.0" lcCooperative="0.1" lcSpeedGain="1.5" accel="2.5" decel="4.5" emergencyDecel="9.0"/>\n')
    f.write('  <vType id="bg" vClass="passenger" length="4.5" width="1.8" color="255,255,0" speedFactor="0.8" sigma="0.8" minGap="2.5" lcStrategic="1.0" lcCooperative="1.0" lcSpeedGain="0.1" accel="1.5" decel="3.0"/>\n')
    
    bg_generated = 0
    vehicles = []
    while bg_generated < args.bg:
        start_edge = random.choice(edge_ids)
        end_edge = random.choice(edge_ids)
        try:
            path, cost = net.getShortestPath(net.getEdge(start_edge), net.getEdge(end_edge), vClass="passenger")
            if path and len(path) > 1:
                route_edges = " ".join([e.getID() for e in path])
                depart_time = random.randint(0, 300)
                vehicles.append({
                    "type": "bg",
                    "id": f"bg_{bg_generated}",
                    "route_id": f"bg_r_bg_{bg_generated}",
                    "route_edges": route_edges,
                    "depart": depart_time
                })
                bg_generated += 1
        except Exception:
            pass

    taxi_generated = 0
    while taxi_generated < args.taxis:
        start_edge = random.choice(edge_ids)
        end_edge = random.choice(edge_ids)
        try:
            path, cost = net.getShortestPath(net.getEdge(start_edge), net.getEdge(end_edge), vClass="taxi")
            if path and len(path) > 1:
                route_edges = " ".join([e.getID() for e in path])
                vehicles.append({
                    "type": "taxi",
                    "id": f"taxi_{taxi_generated}",
                    "route_id": f"taxi_r{taxi_generated}",
                    "route_edges": route_edges,
                    "depart": 0
                })
                taxi_generated += 1
        except Exception:
            pass
            
    # Sort vehicles strictly by depart time to prevent SUMO from discarding them
    vehicles.sort(key=lambda v: v["depart"])
    
    for v in vehicles:
        f.write(f'  <route id="{v["route_id"]}" edges="{v["route_edges"]}" />\n')
        f.write(f'  <vehicle id="{v["id"]}" type="{v["type"]}" route="{v["route_id"]}" depart="{v["depart"]}" departLane="best" departSpeed="max" departPos="random" />\n')
        
    f.write('</routes>\n')
print(f"Generated new routes.rou.xml with {args.bg} background cars and {args.taxis} taxis")
