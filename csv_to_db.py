import csv
import sqlite3


CSV_FILE = "data/24hour_end_1.csv"
DB_FILE  = "db_to_sumo.db"
SQL_FILE = "db_to_sumo.sql"
MAX_ROWS = 200


# 【AI 辅助记录】
# 功能：读取 CSV 文件
# 第 1 轮：文件打开全是乱码，或者直接报错
# 我：我用 Python 打开这个 csv 文件，有时候打印出来的字是乱的，
#     有时候直接报错说什么 'utf-8' codec can't decode。这怎么办啊？
# AI：这是因为 CSV 文件的编码格式有时候不标准。
#     我们可以在 open() 函数里加两个参数：
#     1. `encoding="utf-8"`：尽量用 utf-8 去读。
#     2. `errors="ignore"`：如果遇到实在读不懂的字符，直接跳过它，
#        不要让整个程序崩溃。
#
# 第 2 轮：文件太大了，电脑卡半天，我只想先看前200行
# 我：这个 csv 文件有几百万行，我每次运行都要等好久。
#     能不能先只读前 200 行让我试试水？
# AI：可以。我们用 `enumerate` 来循环，它会自动帮我们数行数 (i)。
#     当 `i` 大于等于你设定的 limit (200) 时，直接 `break` 跳出循环，
#     这样后面的内容就不会读了。
def get_csv_data(path, limit):
    rows = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        # enumerate(f) 会同时返回“行数(i)”和“行内容(row)”
        for i, row in enumerate(csv.DictReader(f)):
            if i >= limit: 
                break # 到了200行就停止，不读了
            rows.append(row)
    return rows


# 【AI 辅助学习记录】
# 功能：通过 .sql 文件建表
# 第 1 轮：SQL 文件里有好多句命令，一起执行报错
# 我：我把建表的代码都写在那个 db_to_sumo.sql 文件里了，里面有好几个
#     CREATE TABLE，用分号隔开的。我在 Python 里直接读出来运行报错，
#     说好像一次只能跑一句。这要怎么拆开来啊？
# AI：SQL 文件本质上就是个长字符串。我们可以用 Python 的字符串分割功能，
#     也就是 `.split(';')`，遇到分号就切一刀，把它变成一个列表，
#     列表里每一项就是一句单独的 SQL。然后我们用 for 循环一句句去执行就行。
#     注意：切完之后可能会有空字符串，要加个 `if s.strip()` 判断一下，
#     空的就跳过不执行。
def setup_database(conn, sql_path):
    with open(sql_path, "r", encoding="utf-8") as f:
        # 按分号切割成一条条 SQL 语句
        sql_statements = f.read().split(";")
        
        for s in sql_statements:
            # 排除掉空行或者只有空格的无效内容
            if s.strip():
                try: 
                    conn.execute(s)
                except: 
                    # 如果某一句执行错了（比如表已经存在），忽略它，继续执行下一句
                    pass 
    conn.commit()
    print("数据库表准备就绪")


# 【AI 辅助学习记录】
# 功能：把 CSV 数据插入数据库
# 第 1 轮：好多列要转数字
# 我：CSV 里读出来的都是字，但是数据库里有些字段是数字。
#     有什么办法呢？
# AI：你可以用 `or` 这个关键字。比如 `float(r.get("passenger_count") or 0)`。
#     它的意思是：如果前面那个值是空的，就直接用后面的 0。
#
# 第 2 轮：一行行插太慢了，能不能快点？
# 我：现在虽然只有200行，但如果以后有几万行，一行行插会不会很慢？
# AI：会的。所以我们用 `executemany`。你先把所有要插的数据都打包进一个
#     大列表 (t_vals)，然后最后只调用一次 `executemany`，这样速度快很多。
def insert_data(conn, rows):
    # 修改后的安全写法
    sql_trip = """INSERT INTO trips (
        pickup_datetime, dropoff_datetime, pickup_edge, dropoff_edge, 
        passenger_count, trip_distance, 
        pickup_x, pickup_y, dropoff_x, dropoff_y
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"""
    
    sql_req = "INSERT INTO simulation_tasks (dispatch_time, origin_edge, dest_edge, status) VALUES (?, ?, ?, 'CREATED')"
    
    # 准备两个空列表，用来装打包好的数据
    t_vals, r_vals = [], []
    
    for r in rows:
        try:
            # 1. 提取字符串字段
            p_time = r.get("pickup_datetime", "")
            d_time = r.get("dropoff_datetime", "")
            te = r.get("te", "")
            fe = r.get("fe", "")
            
            # 2. ai补全安全转换数字
            p_count = int(float(r.get("passenger_count") or 0))
            trip_dist = float(r.get("trip_distance") or 0)
            
            # 3. 经纬度坐标
            p_x = float(r.get("pickup_longitude") or 0)
            p_y = float(r.get("pickup_latitude") or 0)
            d_x = float(r.get("dropoff_longitude") or 0)
            d_y = float(r.get("dropoff_latitude") or 0)
            
            # 4. 打包成元组，放进列表里
            t_vals.append((p_time, d_time, te, fe, p_count, trip_dist, p_x, p_y, d_x, d_y))
            r_vals.append((p_time, te, fe))
            
        except: 
            continue 
            
    # 5. 批量执行插入
    conn.executemany(sql_trip, t_vals)
    conn.executemany(sql_req, r_vals)
    conn.commit()
    
    return len(t_vals)

if __name__ == "__main__":
    print(f"正在读取 CSV 文件：{CSV_FILE}...")
    data = get_csv_data(CSV_FILE, MAX_ROWS)
    print(f"成功读取 {len(data)} 行数据 (已限制前 {MAX_ROWS} 行)")

    print("正在连接数据库...")
    conn = sqlite3.connect(DB_FILE)
    setup_database(conn, SQL_FILE)

    print("正在往数据库里插入数据...")
    count = insert_data(conn, data)

    conn.close()
    print(f"全部搞定！一共向数据库插入了 {count} 条有效数据。")