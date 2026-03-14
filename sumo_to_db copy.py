import sqlite3
import os

# 尝试导入 SUMO 库，小白通常直接复制网上的导入写法，报错了再问
try:
    import traci
    from sumolib import checkBinary
    import sumolib
except Exception:
    traci = None
    sumolib = None

# ================= 配置区 (小白版：直接写死文件名) =================
# 之前我想搞什么环境变量，结果太麻烦总是配不对，AI 让我直接写文件名，
# 只要文件和代码放在同一个文件夹里就能跑，简单多了。
DB_FILE = "sumo_to_db.db"
NET_FILE = "sumo_inputs/convert-1.net.xml"
GUI_FILE = "sumo_inputs/gui-settings.xml"
SQL_FILE = "sumo_to_db.sql"

# 动态生成的文件也放在 sumo_inputs 目录下
ROUTE_FILE = "sumo_inputs/routes.rou.xml"
CFG_FILE = "sumo_inputs/sumo.sumocfg"

VEH_COUNT = 30   # 车数量，随便设的
STEPS = 300      # 仿真步数
DELAY = "100"    # 延迟

# 【AI 辅助记录】
# ---------------------------------------------------------
# 1. 我当时遇到的问题：
#    - 我不知道 SUMO 的路线文件 (.rou.xml) 格式太麻烦了，要写好多标签。
#    - 我想让车在路网里跑，但我不知道哪些路是通的。
#    - 我自己写了几条路，结果仿真时报错说“车辆无法插入”，说路径不通。
#
# 2. 我发给 AI 的内容 (直接复制报错 + 大白话)：
#    "我手动写的路线文件报错了，说 'Vehicle cannot insert'，可能是路不通。
#     我有 net.xml 文件，能不能用 python 自动找一条从起点到终点的路？
#     我不想要太复杂的逻辑，只要能让车动起来就行。
#     还有，我想生成 30 辆车，让它们每隔 2 秒发一辆，怎么写比较快？
#     请帮我写个函数自动生成这个 XML 文件，直接存到当前文件夹。"
#
# 3. AI 帮我改了什么：
#    - 它用了 `sumolib.net.readNet` 读路网，然后用 `getShortestPath` 自动算路，这样就不会报“路不通”了。
#    - 它帮我写了循环，自动生成 30 辆车的 XML 标签，不用我手敲几十行代码。
#    - 它把文件直接存成了 `routes.rou.xml`，没搞什么临时文件夹，方便我查看。
# ---------------------------------------------------------
def build_route(net):
    """构建一个简单的路由 (这是 AI 帮我写的，我自己不会算最短路径)"""
    edges = [e for e in net.getEdges() if not e.isSpecial()]
    if len(edges) < 2:
        return [edges[0].getID()] if edges else []
    
    start = edges[0]
    end = edges[-1]
    
    try:
        # AI 说用这个函数可以自动算出路，不然我根本不知道哪条路能走
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
    
    # 这里原本我想写 30 遍 <vehicle...>，AI 说用循环生成
    for i in range(VEH_COUNT):
        depart_time = i * 2 
        lines.append(f'  <vehicle id="veh_{i}" type="taxi" route="r0" depart="{depart_time}" departLane="best" departSpeed="max"/>')
    
    lines.append('</routes>')
    
    with open(route_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines) + "\n")
    return route_file

def write_cfg(route_file):
    """生成 SUMO 配置文件 sumo.sumocfg"""
    cfg_file = CFG_FILE
    
    # 这个列表是 AI 帮我拼好的 XML 结构，我自己写容易漏标签
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
        # 如果找不到 sql 文件，程序会停在这里，这也是 AI 加的提示
        raise FileNotFoundError(f"找不到数据库文件：{SQL_FILE}，请先创建它！")
    
    cur = conn.cursor()
    with open(SQL_FILE, 'r', encoding='utf-8') as f:
        sql_script = f.read()
    
    cur.executescript(sql_script)
    conn.commit()
    print("数据库表创建完成。")

# 【AI 辅助记录】
# ---------------------------------------------------------
# 1. 我当时遇到的问题：
#    - 我知道要用 `traci` 控制仿真，但不知道具体每一步该调什么函数。
#    - 文档太多了，我看晕了。我想获取车的位置、速度，并存到数据库里。
#    - 还有，仿真结束后，我想算一下每辆车跑了多远。但我不会算两点间的距离，也不想搞太复杂的数学。
#    - 程序老是在中间崩掉，数据库连接没关闭。
#
# 2. 我发给 AI 的内容 (直接复制报错 + 大白话)：
#    "请给我一个 traci 的主循环模板。
#    我需要每一步都获取所有车的 ID、位置 (x,y)、速度和所在路段。
#    然后把这些存到 sqlite 数据库的 vehicle_trajectories 表里。
#    仿真结束后，帮我算一下每辆车的总时间和平均速度。
#    距离怎么算太麻烦了，能不能用速度简单估算一下？
#    还有，记得帮我把数据库连接和 traci 关闭，不然老是报错。"
#
# 3. AI 帮我改了什么：
#    - 它给了我这个 `for step in range(STEPS)` 的循环结构，里面填好了 `traci.simulationStep()`。
#    - 它列出了 `traci.vehicle.getPosition`, `getSpeed` 等我不知道的函数。
#    - 关于距离，它说“严谨做法很复杂”，然后帮我用 `速度 * 时间` 做了个简单的估算，满足作业要求就行。
#    - 它加了 `try...finally` 块，确保就算我按 Ctrl+C 中断，数据库和 SUMO 也能正常关闭。
# ---------------------------------------------------------
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
                # 获取实时数据，这些函数名都是我查不到，问 AI 要的
                edge = traci.vehicle.getRoadID(vid)
                x, y = traci.vehicle.getPosition(vid)
                speed = traci.vehicle.getSpeed(vid)
                
                # 【关键 AI 辅助点】这里原本我不会算距离
                # 我问 AI“能不能简单估算一下”，它就用 步数*速度 糊弄了一个算法
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
                
                # 【关键 AI 辅助点】这个平均速度和总距离的算法也是 AI 给的“简易版”
                # 它说：“如果不要求高精度，可以用最大速度的一半来估算平均速度”
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
        # AI 强调一定要加 finally，不然数据库锁死打不开
        conn.close()
        traci.close()
        print("连接已关闭。")

if __name__ == "__main__":
    main()