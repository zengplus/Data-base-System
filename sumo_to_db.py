import sqlite3
import os
import traci
from sumolib import checkBinary
import sumolib


DB_FILE = "sumo_to_db.db"
NET_FILE = "sumo_inputs/convert-1.net.xml"
GUI_FILE = "sumo_inputs/gui-settings.xml"
SQL_FILE = "sumo_to_db.sql"

ROUTE_FILE = "sumo_inputs/routes.rou.xml"
CFG_FILE = "sumo_inputs/sumo.sumocfg"

VEH_COUNT = 30   # 车数量，随便设的
STEPS = 300      # 仿真步数
DELAY = "100"    # 延迟


# 【AI 辅助学习记录】
# 功能：自动算路生成路由
# 第 1 轮：生成一个简单的路由
# 我：我有一个 net.xml 文件，你能不能帮我写个 Python 脚本生成一个 routes.rou.xml？
#      我对 SUMO 不太熟，只要能让车在上面跑起来就行。
# AI：为了防止车在地图里因为路不通而报错，我用 sumolib 库帮你自动读取地图，并计算一条最短路径。
#
# 第 2 轮：
# 我：车跑起来，但是只有一辆车，能不能帮我生成 30 辆车进行测试
# AI：好的，我们加一个 for 循环，让 Python 帮你生成 30 个 <vehicle> 标签，
#     出发时间设为每隔 2 秒发一辆。
def build_route(net):
    """构建一个简单的路由 (这是 AI 帮我写的，我自己不会算最短路径)"""
    edges = [e for e in net.getEdges() if not e.isSpecial()]
    if len(edges) < 2:
        return [edges[0].getID()] if edges else []
    
    start = edges[0]
    end = edges[-1]
    
    try:
        path, _ = net.getShortestPath(start, end)
        if not path:
            return [start.getID()]
        return [e.getID() for e in path]
    except Exception:
        return [start.getID()]

def write_routes(net):
    """生成路线文件 routes.rou.xml"""
    route_file = ROUTE_FILE
    
    edge_ids = build_route(net)
    if not edge_ids:
        raise ValueError("无法生成有效的路线")
        
    edges_str = " ".join(edge_ids)
    
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<routes>']
    lines.append('  <vType id="taxi" vClass="passenger" length="4.0" width="1.6"/>')
    lines.append(f'  <route id="r0" edges="{edges_str}"/>')
    
    for i in range(VEH_COUNT):
        depart_time = i * 2 
        lines.append(f'  <vehicle id="veh_{i}" type="taxi" route="r0" depart="{depart_time}" departLane="best" departSpeed="max"/>')
    
    lines.append('</routes>')
    
    with open(route_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines) + "\n")
    return route_file


# 【AI 辅助学习记录】
# 功能：生成配置文件
# 第 1 轮：XML 标签老是写错，不是少了'/'就是拼错单词
# 我：每次生成完 routes.rou.xml，我都要手动去改 sumo.sumocfg，
#      而且我老是写错 XML 标签，SUMO 就报错说 not well-formed。
#      能不能让 Python 顺便帮我把这个配置文件也生成了？
# AI：可以。我们把 XML 的每一行都当作字符串，放在一个列表里，
#      最后用 `"\n".join(列表)` 拼起来写进文件。这样格式绝对工整。
def write_cfg(route_file):
    """生成 SUMO 配置文件 sumo.sumocfg"""
    cfg_file = CFG_FILE
    
    cfg = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<configuration>',
        '  <input>',
        f'    <net-file value="{os.path.basename(NET_FILE)}"/>',
        f'    <route-files value="{os.path.basename(route_file)}"/>',
        '  </input>',
        '  <time>',
        '    <begin value="0"/>',
        '    <end value="1000000000"/>',
        '  </time>',
        '</configuration>'
    ]
    
    with open(cfg_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(cfg))
    return cfg_file

def init_db(conn):
    """初始化数据库"""
    if not os.path.exists(SQL_FILE):
        raise FileNotFoundError(f"找不到数据库文件：{SQL_FILE}，请先创建它！")
    
    cur = conn.cursor()
    with open(SQL_FILE, 'r', encoding='utf-8') as f:
        sql_script = f.read()
    
    cur.executescript(sql_script)
    conn.commit()
    print("数据库表创建完成。")


# 【AI 辅助学习记录】
# 功能：Traci 主循环 & 数据记录
# 第 1 轮：Traci 怎么启动？怎么获取车的位置？
# 我：我知道要用 Traci 来控制仿真，能不能给我一个最简单的模板
#      怎么在循环里获取所有车的 ID、位置 (x,y)、速度和在哪条路上？
# AI：
#      1. 启动用 `traci.start([sumo_gui, "-c", 配置文件, ...])`。
#      2. 循环用 `for step in range(STEPS)`，里面一定要调用 `traci.simulationStep()`。
#      3. 获取车辆列表用 `traci.vehicle.getIDList()`。
#      4. 获取具体数据用：
#         - `getRoadID(vid)` : 在哪条路
#         - `getPosition(vid)` : 坐标
#         - `getSpeed(vid)` : 速度
#
# 第 2 轮：距离怎么算？我不想算经纬度，太麻烦了
# 我：位置和速度我都存下来了！但是最后还要算总距离。
# AI：理解！如果不要求高精度，我们可以用“物理公式”来估算：
#      距离 ≈ 速度 × 时间。
#      或者更简单一点，我们记录下最高速度，最后用 `最高速度 * 0.5 * 总时间` 来估算。
#      虽然不精确，但对于作业演示来说完全够用了。
#
# 第 3 轮：程序崩了之后，数据库就锁死了，打不开
# 我：我有时候按 Ctrl+C 强制退出，或者程序报错退出，
#      下次再运行就说数据库被锁住了，或者 SUMO 的端口还被占着。
# AI：这是因为你没有正确关闭连接。你一定要用 `try...finally` 结构。
#      不管程序是正常结束、报错还是被你按 Ctrl+C，`finally` 里的代码
#      (conn.close() 和 traci.close()) 都一定会执行！
def main():
    # 检查依赖
    if traci is None or sumolib is None:
        print("错误：缺少 traci 或 sumolib 库。请确保已安装 SUMO。")
        return
    
    if not os.path.exists(NET_FILE):
        print(f"错误：找不到路网文件：{NET_FILE}")
        return
    
    print("正在加载路网...")
    net = sumolib.net.readNet(NET_FILE)
    
    print("正在生成路线文件...")
    route_file = write_routes(net)
    
    print("正在生成配置文件...")
    cfg_file = write_cfg(route_file)
    
    # 启动 SUMO
    sumo_gui = checkBinary("sumo-gui")
    print("正在启动 SUMO GUI...")
    
    # 这串参数也是 AI 帮我配的
    traci.start([
        sumo_gui, 
        "-c", cfg_file, 
        "--start", 
        "--delay", DELAY,
        "--no-step-log"
    ])
    
    # 连接数据库
    print("正在连接数据库...")
    conn = sqlite3.connect(DB_FILE)
    init_db(conn)
    cur = conn.cursor()
    
    vehicle_trips = {}
    
    print(f"开始仿真循环 (共 {STEPS} 步)...")
    
    try:
        for step in range(STEPS):
            traci.simulationStep()
            vehicles = traci.vehicle.getIDList()
            
            for vid in vehicles:
                # 获取实时数据
                edge = traci.vehicle.getRoadID(vid)
                x, y = traci.vehicle.getPosition(vid)
                speed = traci.vehicle.getSpeed(vid)
                
                # 【关键 AI 辅助点】
                # 简单的算法 步数*速度 
                dist_estimate = step * speed 
                
                # 更新插入语句：表名统一，字段名统一
                cur.execute(
                    "INSERT INTO vehicle_trajectories (step, vehicle_id, edge_id, x, y, speed, distance_from_start) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (step, vid, edge, x, y, speed, dist_estimate)
                )
                
                if step == 0:
                    vehicle_trips[vid] = {
                        'start_step': step,
                        'start_edge': edge,
                        'max_speed': speed,
                    }
                else:
                    if vid in vehicle_trips:
                        current_max = vehicle_trips[vid].get('max_speed', 0)
                        vehicle_trips[vid]['max_speed'] = max(current_max, speed)

        print("仿真结束，正在处理最终数据...")
        
        # 汇总数据
        for vid, trip_info in vehicle_trips.items():
            last_pos = cur.execute(
                "SELECT step FROM vehicle_trajectories WHERE vehicle_id = ? ORDER BY step DESC LIMIT 1",
                (vid,)
            ).fetchone()
            
            if last_pos:
                end_step = last_pos[0]
                start_step = trip_info['start_step']
                total_time = end_step - start_step
                
                # 【关键 AI 辅助点】
                # 用最大速度的一半来估算平均速度
                avg_speed_est = trip_info['max_speed'] * 0.5 
                total_distance = total_time * avg_speed_est if total_time > 0 else 0
                
                final_avg_speed = total_distance / total_time if total_time > 0 else 0
                
                # 更新插入语句：trips 表结构更新
                # pickup_datetime -> start_step, dropoff_datetime -> end_step
                # pickup_edge -> start_edge, dropoff_edge -> end_edge
                cur.execute("""
                    INSERT INTO trips (
                        vehicle_id, pickup_datetime, dropoff_datetime, pickup_edge, dropoff_edge, 
                        trip_distance, max_speed, avg_speed
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    vid, start_step, end_step, trip_info['start_edge'], trip_info['start_edge'],
                    total_distance, trip_info['max_speed'], final_avg_speed
                ))
        
        conn.commit()
        print(f"成功！数据已保存到：{DB_FILE}")
        
    except KeyboardInterrupt:
        print("\n仿真被用户中断。")
    finally:
        # AI补全
        conn.close()
        traci.close()
        print("连接已关闭。")

if __name__ == "__main__":
    main()