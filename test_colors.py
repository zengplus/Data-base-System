import sqlite3
import pandas as pd

conn = sqlite3.connect("dispatch.db")

print("--- 当前各状态车辆总数 ---")
df_taxis = pd.read_sql_query("SELECT status, COUNT(*) as count FROM taxis GROUP BY status", conn)
print(df_taxis)

print("\n--- 历史派单记录（有多少车接到了单） ---")
df_assign = pd.read_sql_query("SELECT COUNT(DISTINCT taxi_id) as active_taxis FROM assignments", conn)
print(df_assign)

conn.close()
