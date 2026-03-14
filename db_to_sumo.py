import sqlite3
import subprocess
import shutil

DB_FILE = "db_to_sumo.db"
MAX_ROWS = 200
SUMO_DELAY = "100"

FILE_HEADER = "sumo_inputs/route_header.xml"
FILE_FOOTER = "sumo_inputs/route_footer.xml"
FILE_TEMPLATE_CFG = "sumo_inputs/sumo_template.sumocfg"
FILE_OUTPUT_ROUTE = "sumo_inputs/routes.rou.xml"
FILE_OUTPUT_CFG = "sumo_inputs/sumo.sumocfg"

# 【AI 辅助记录】
# 功能：生成 SUMO 路由文件
# 第 1 轮：遇到报错
# 我：代码报错了：'could not convert string to float'。
# AI：这是因为你试图把一个不是数字的字符串（比如空值）变成浮点数。
#     你需要检查一下数据库里 `dispatch_time` 字段是不是有空的或者脏数据。
#     建议加个 try...except 来处理。
#
# 第 2 轮：解决报错后，发现文件格式不对
# 我：按照你说的改了，不报错了。但是生成的 routes.rou.xml 文件用 SUMO 打不开，
#     说格式不对。
# AI：XML 文件必须有完整的 <routes> 标签包裹。你需要在写数据前先把 header 
#     的内容读进去写完，最后再写 footer。
#
# 第 3 轮：车没有出现
# 我：文件能打开了，但是我发现车没有出现
# AI：在写入文件之前，你需要对从数据库取出的 list 进行排序。
#     Python 里可以用 sorted() 函数，通过 key=lambda x: ... 来指定按时间排。
# 最终修改：以上三步，写成了下面的 build_routes 函数。
def build_routes(rows):
    with open(FILE_OUTPUT_ROUTE, "w", encoding="utf-8") as f_out:
        # 1. 写入头部
        with open(FILE_HEADER, "r", encoding="utf-8") as f_head:
            f_out.write(f_head.read())
        f_out.write("\n") 
        
        # 2. 定义排序键函数
        # 同时也处理了第1轮的报错问题：如果时间转失败，默认给0
        def get_safe_time(row):
            try: 
                return float(row[0])
            except (ValueError, TypeError): 
                return 0.0
            
        # 3. 排序并循环写入
        # ai补全 sorted(..., key=get_safe_time) 
        for i, (t, te, fe) in enumerate(sorted(rows, key=get_safe_time)):
            # 过滤掉起点或终点为空的无效数据
            if not te or not fe: 
                continue
                
            # 再次尝试安全转换时间
            try: 
                depart_time = int(float(t))
            except: 
                # ai补全建议，如果实在转换失败，用序号i简单推算一个时间，保证车能出来
                depart_time = i * 2 
            
            # 生成 XML 节点
            # ai补全加了 max(0, ...) 防止时间出现负数
            xml_line = f'  <trip id="taxi_{i}" type="taxi" depart="{max(0, depart_time)}" from="{te}" to="{fe}"/>\n'
            f_out.write(xml_line)
        
        # 4. 写入尾部
        with open(FILE_FOOTER, "r", encoding="utf-8") as f_foot:
            f_out.write(f_foot.read())
            
    return FILE_OUTPUT_ROUTE




# 【AI 辅助学习记录】
# 功能：主程序入口
# 第 1 轮：读数据库读取出错no such table
# 我：我有个 SQLite 数据库文件，但是有时候会读取出错了no such table
# AI：表名拼写错了（比如少写了个字母）。也需要检查文件路径，并且用 try...except 把代码包起来，
#     这样报错时程序不会直接崩溃，而是会告诉你哪里错了。
#
# 第 2 轮：数据太多了，我只想取前200条怎么办？
# 我：数据库里有几万条数据，全取出来程序会卡。怎么只取前 N 条？
# AI：在 SQL 里加 LIMIT ?，然后用元组 (MAX_ROWS,) 把参数传进去。
#     特别注意：Python 里 sqlite3 的参数必须是元组，哪怕只有一个参数，后面也要加逗号，
#     也就是 (200,)，不能写成 (200)。
#
# 第 3 轮：配置文件怎么办？
# 我：每次都要手动去点开那个 .sumocfg 文件，检查里面的文件名对不对，
#      有时候忘了改，SUMO 就报错找不到文件。
# AI：可以用 shutil.copy() 直接在代码里复制文件，自动生成 sumo.sumocfg。
def main():
    # 1. 读取数据库
    try:
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("SELECT dispatch_time, origin_edge, dest_edge FROM simulation_tasks ORDER BY dispatch_time LIMIT ?", (MAX_ROWS,))
        rows = cur.fetchall()
        conn.close()
    except Exception as e:
        print(f"数据库读取失败: {e}")
        return

    if not rows:
        print("数据库里没有数据")
        return

    print(f"成功读取 {len(rows)} 条数据，正在生成路由文件...")
    
    # 2. 调用上面的函数生成 XML
    build_routes(rows)
    
    # 3. 自动复制配置文件
    try:
        shutil.copy(FILE_TEMPLATE_CFG, FILE_OUTPUT_CFG)
    except FileNotFoundError:
        print(f"错误：找不到模板文件 {FILE_TEMPLATE_CFG}，请检查路径。")
        return
    
    # 4. 启动 SUMO GUI
    print("正在启动 SUMO 仿真界面...")
    # 查看官方文档增加的下面的参数
    subprocess.Popen(["sumo-gui", "-c", FILE_OUTPUT_CFG, "--start", "--delay", SUMO_DELAY, "--tls.all-off"])
    print("全部完成！")

if __name__ == "__main__":
    main()