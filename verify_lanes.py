import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
import sumolib
import config

def verify_lane_distribution():
    net = sumolib.net.readNet(config.NET_FILE)
    
    edges = net.getEdges()
    min_x = min_y = float('inf')
    max_x = max_y = float('-inf')
    for e in edges:
        shape = e.getShape()
        for x, y in shape:
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x)
            max_y = max(max_y, y)
            
    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2
    radius_sq = ((max_x - min_x) * 0.25) ** 2
    
    outer_lanes_4 = []
    outer_lanes_3 = []
    outer_lanes_2 = []
    
    for e in edges:
        if not e.getID().startswith(":"):
            shape = e.getShape()
            xs, ys = zip(*shape)
            cx, cy = sum(xs)/len(xs), sum(ys)/len(ys)
            dist_sq = (cx - center_x)**2 + (cy - center_y)**2
            is_center = dist_sq <= radius_sq
            
            lane_num = e.getLaneNumber()
            
            if not is_center:
                if lane_num >= 4:
                    outer_lanes_4.append(e.getID())
                elif lane_num == 3:
                    outer_lanes_3.append(e.getID())
                elif lane_num == 2:
                    outer_lanes_2.append(e.getID())
                    
    print("=== 路网车道分布验证 ===")
    print(f"路网总边数 (排除交叉口内部边): {len([e for e in edges if not e.getID().startswith(':')])}")
    print(f"外围 >= 4车道 数量: {len(outer_lanes_4)}")
    print(f"外围 == 3车道 数量: {len(outer_lanes_3)}")
    print(f"外围 == 2车道 数量: {len(outer_lanes_2)}")

if __name__ == "__main__":
    verify_lane_distribution()
