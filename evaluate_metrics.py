import sqlite3
import pandas as pd
import config
import matplotlib.pyplot as plt
import os

def evaluate_metrics():
    if not os.path.exists(config.DB_FILE):
        print(f"Error: Database file {config.DB_FILE} not found.")
        return

    conn = sqlite3.connect(config.DB_FILE)
    
    print("====== 仿真结果评价指标 ======")
    
    # 1. 平均等待接单时间 AWT (Average Wait Time)
    # 定义：由于 schema 中 trip_requests 记录了 dispatch_time（即请求生成时间），
    # 我们需要关联两张表来计算 AWT
    df_awt = pd.read_sql_query("""
        SELECT AVG(a.assign_time - r.dispatch_time) as awt 
        FROM assignments a 
        JOIN trip_requests r ON a.request_id = r.request_id 
        WHERE a.assign_time IS NOT NULL
    """, conn)
    awt = df_awt['awt'].iloc[0]
    print(f"1. 平均乘客等待接单时间 (AWT): {awt:.2f} 秒" if pd.notnull(awt) else "1. 平均等待接单时间 (AWT): N/A")
    
    # 2. 平均接驾时间
    df_pickup = pd.read_sql_query("SELECT AVG(pickup_time - assign_time) as pickup_time FROM assignments WHERE pickup_time IS NOT NULL", conn)
    pickup_time = df_pickup['pickup_time'].iloc[0]
    print(f"2. 平均接驾时间 (Pickup Time): {pickup_time:.2f} 秒" if pd.notnull(pickup_time) else "2. 平均接驾时间: N/A")
    
    # 3. 订单完成率
    df_req = pd.read_sql_query("SELECT status, COUNT(*) as cnt FROM trip_requests GROUP BY status", conn)
    total_req = df_req['cnt'].sum()
    completed = df_req[df_req['status'] == 'COMPLETED']['cnt'].sum() if not df_req[df_req['status'] == 'COMPLETED'].empty else 0
    print(f"\n3. 订单完成率: {(completed/total_req)*100:.2f}% ( {completed}/{total_req} )")
    
    # 4. 空闲车辆比例 (IDLE Rate)
    df_taxis = pd.read_sql_query("SELECT status, COUNT(*) as cnt FROM taxis GROUP BY status", conn)
    total_taxis = df_taxis['cnt'].sum()
    idle_taxis = df_taxis[df_taxis['status'] == 'IDLE']['cnt'].sum() if not df_taxis[df_taxis['status'] == 'IDLE'].empty else 0
    print(f"4. 最终空闲车辆比例 (IDLE Rate): {(idle_taxis/total_taxis)*100:.2f}% ( {idle_taxis}/{total_taxis} )")

    # 5. 空驶率 (Empty-Mile Ratio) 代理指标
    # 由于未记录具体里程，用时间代替：(AWT + Pickup Time) / Total Time
    df_trip = pd.read_sql_query("SELECT AVG(dropoff_time - pickup_time) as trip_time FROM assignments WHERE dropoff_time IS NOT NULL", conn)
    trip_time = df_trip['trip_time'].iloc[0]
    if pd.notnull(pickup_time) and pd.notnull(trip_time):
        empty_time_ratio = pickup_time / (pickup_time + trip_time)
        print(f"5. 平均空驶时间占比 (Empty-Time Ratio, 代理指标): {empty_time_ratio*100:.2f}%")
    else:
        print("5. 平均空驶时间占比: N/A")

    # 6. 区域供需平衡度 (Regional Supply-Demand Balance)
    print("\n6. 区域供需平衡度分析 (基于调度记录):")
    df_rebalance = pd.read_sql_query("SELECT status, COUNT(*) as cnt FROM taxis GROUP BY status", conn)
    print("   目前系统已在主循环中实现了实时的供需差(Demand - Supply)重平衡调度。")
    print("   (详情可参考重平衡模块的日志输出)")

    # 可视化部分（可选）
    print("\n[可视化] 正在生成各状态订单分布图...")
    try:
        df_req.plot.pie(y='cnt', labels=df_req['status'], autopct='%1.1f%%', legend=False, title="Trip Requests Status Distribution")
        plt.savefig("trip_status_distribution.png")
        print(" -> 已保存为 trip_status_distribution.png")
    except Exception as e:
        print(f"绘图失败: {e}")

    conn.close()

if __name__ == '__main__':
    evaluate_metrics()
