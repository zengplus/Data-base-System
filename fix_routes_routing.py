import sumolib
import random

net = sumolib.net.readNet('/home/shu/Documents/Data-base-System/sumo_inputs/convert-1.net.xml')
edges = net.getEdges()
edge_ids = [e.getID() for e in edges if not e.getID().startswith(':') and e.allows("passenger")]

with open("/home/shu/Documents/Data-base-System/sumo_inputs/routes.rou.xml", "w") as f:
    f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    f.write('<routes>\n')
    # 出租车稍微快一点，且变道积极（lcSpeedGain 高），但不至于引发碰撞 (去掉 jmIgnoreFoeProb 等引发崩溃的极端参数)
    f.write('  <vType id="taxi" vClass="taxi" length="4.0" width="1.6" color="0,255,0" speedFactor="1.2" sigma="0.5" lcStrategic="1.0" lcCooperative="0.1" lcSpeedGain="1.5" accel="2.5" decel="4.5" emergencyDecel="9.0"/>\n')
    # 背景车速度较慢，变道合作度高（让行），不频繁超车
    f.write('  <vType id="bg" vClass="passenger" length="4.5" width="1.8" color="255,255,0" speedFactor="0.8" sigma="0.8" minGap="2.5" lcStrategic="1.0" lcCooperative="1.0" lcSpeedGain="0.1" accel="1.5" decel="3.0"/>\n')
    
    # generate 300 background cars (减少数量，确保不堵死)
    for i in range(300):
        start_edge = random.choice(edge_ids)
        end_edge = random.choice(edge_ids)
        try:
            path, cost = net.getShortestPath(net.getEdge(start_edge), net.getEdge(end_edge), vClass="passenger")
            if path and len(path) > 1:
                route_edges = " ".join([e.getID() for e in path])
                f.write(f'  <route id="bg_r_bg_{i}" edges="{route_edges}" />\n')
                depart_time = random.randint(0, 300)
                f.write(f'  <vehicle id="bg_{i}" type="bg" route="bg_r_bg_{i}" depart="{depart_time}" departLane="best" departSpeed="max" departPos="random" />\n')
        except Exception:
            pass

    # generate 300 taxis
    for i in range(300):
        start_edge = random.choice(edge_ids)
        end_edge = random.choice(edge_ids)
        try:
            path, cost = net.getShortestPath(net.getEdge(start_edge), net.getEdge(end_edge), vClass="taxi")
            if path and len(path) > 1:
                route_edges = " ".join([e.getID() for e in path])
                f.write(f'  <route id="taxi_r{i}" edges="{route_edges}" />\n')
                f.write(f'  <vehicle id="taxi_{i}" type="taxi" route="taxi_r{i}" depart="0" departLane="best" departSpeed="max" departPos="random" />\n')
        except Exception:
            pass
            
    f.write('</routes>\n')
print("Generated new routes.rou.xml with 300 background cars and 300 taxis")
