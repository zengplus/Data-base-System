import sqlite3
import pandas as pd

db_path = "/home/shu/Documents/Data-base-System/dispatch.db"
conn = sqlite3.connect(db_path)

print("="*40)
print("1. 出租车当前状态分布 (taxis table)")
print("="*40)
df_taxis = pd.read_sql_query("SELECT status, COUNT(*) as count FROM taxis GROUP BY status", conn)
print(df_taxis.to_string(index=False))

print("\n" + "="*40)
print("2. 订单请求状态分布 (trip_requests table)")
print("="*40)
df_reqs = pd.read_sql_query("SELECT status, COUNT(*) as count FROM trip_requests GROUP BY status", conn)
print(df_reqs.to_string(index=False))

print("\n" + "="*40)
print("3. 订单分配关键指标 (assignments table)")
print("="*40)
df_assign = pd.read_sql_query("""
    SELECT 
        COUNT(*) as total_assignments,
        AVG(pickup_time - assign_time) as avg_pickup_time_steps,
        AVG(dropoff_time - pickup_time) as avg_trip_time_steps
    FROM assignments
""", conn)
print(df_assign.to_string(index=False))

print("\n" + "="*40)
print("4. 完成了至少一单的车辆数")
print("="*40)
df_active = pd.read_sql_query("SELECT COUNT(DISTINCT taxi_id) as active_taxis FROM assignments", conn)
print(df_active.to_string(index=False))

conn.close()
