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
    
    # 1. 乘客等待接单时间 AWT (Average Wait Time)
    df_awt_all = pd.read_sql_query("""
        SELECT AVG(a.assign_time - r.dispatch_time) as awt 
        FROM assignments a 
        JOIN trip_requests r ON a.request_id = r.request_id 
        WHERE a.assign_time IS NOT NULL
    """, conn)
    awt_all = df_awt_all['awt'].iloc[0]

    df_awt_health = pd.read_sql_query("""
        SELECT AVG(a.assign_time - r.dispatch_time) as awt 
        FROM assignments a 
        JOIN trip_requests r ON a.request_id = r.request_id 
        WHERE r.status = 'COMPLETED'
    """, conn)
    awt_health = df_awt_health['awt'].iloc[0]

    print("1. 乘客等待接单时间 (AWT):")
    print(f"   - 所有已接订单平均: {awt_all:.2f} 秒" if pd.notnull(awt_all) else "   - 所有已接订单平均: N/A")
    print(f"   - 最终成功完成的健康订单平均: {awt_health:.2f} 秒" if pd.notnull(awt_health) else "   - 最终成功完成的健康订单平均: N/A")
    
    # 2. 车辆行驶时间深度分析
    df_pickup = pd.read_sql_query("""
        SELECT AVG(a.pickup_time - a.assign_time) as pickup_time 
        FROM assignments a
        JOIN trip_requests r ON a.request_id = r.request_id 
        WHERE r.status = 'COMPLETED' AND a.pickup_time IS NOT NULL
    """, conn)
    pickup_time = df_pickup['pickup_time'].iloc[0]

    df_trip = pd.read_sql_query("""
        SELECT AVG(a.dropoff_time - a.pickup_time) as trip_time 
        FROM assignments a
        JOIN trip_requests r ON a.request_id = r.request_id 
        WHERE r.status = 'COMPLETED' AND a.dropoff_time IS NOT NULL
    """, conn)
    trip_time = df_trip['trip_time'].iloc[0]

    print("\n2. 车辆行驶时间深度分析 (仅统计健康完成订单):")
    print(f"   - 平均空车接驾耗时 (Pickup Time): {pickup_time:.2f} 秒" if pd.notnull(pickup_time) else "   - 平均空车接驾耗时: N/A")
    print(f"   - 平均载客行程耗时 (Trip Time): {trip_time:.2f} 秒" if pd.notnull(trip_time) else "   - 平均载客行程耗时: N/A")
    
    # 3. 订单状态分布
    df_req = pd.read_sql_query("SELECT status, COUNT(*) as cnt FROM trip_requests GROUP BY status", conn)
    total_req = df_req['cnt'].sum()
    completed = df_req[df_req['status'] == 'COMPLETED']['cnt'].sum() if not df_req[df_req['status'] == 'COMPLETED'].empty else 0
    cancelled = df_req[df_req['status'] == 'CANCELLED']['cnt'].sum() if not df_req[df_req['status'] == 'CANCELLED'].empty else 0
    
    print(f"\n3. 订单状态分布 (总数 {total_req}):")
    print(f"   - 成功完成 (COMPLETED): {completed} 单 ({(completed/total_req)*100:.2f}%)")
    print(f"   - 超时死单 (CANCELLED): {cancelled} 单 ({(cancelled/total_req)*100:.2f}%)")
    print("     (注: 较高的 CANCELLED 说明车辆卡死在路上，或接单距离仍过长导致超时被系统熔断)")
    
    # 4. 最终车辆状态分布
    df_taxis = pd.read_sql_query("SELECT status, COUNT(*) as cnt FROM taxis GROUP BY status", conn)
    total_taxis = df_taxis['cnt'].sum()
    idle_taxis = df_taxis[df_taxis['status'] == 'IDLE']['cnt'].sum() if not df_taxis[df_taxis['status'] == 'IDLE'].empty else 0
    rebalancing_taxis = df_taxis[df_taxis['status'] == 'REBALANCING']['cnt'].sum() if not df_taxis[df_taxis['status'] == 'REBALANCING'].empty else 0
    
    print(f"\n4. 最终车辆状态分布 (总数 {total_taxis}):")
    print(f"   - 纯空闲 (IDLE): {idle_taxis} 辆 ({(idle_taxis/total_taxis)*100:.2f}%)")
    print(f"   - 正在重平衡 (REBALANCING): {rebalancing_taxis} 辆 ({(rebalancing_taxis/total_taxis)*100:.2f}%)")

    # 5. 空驶率 (Empty-Mile Ratio) 代理指标
    if pd.notnull(pickup_time) and pd.notnull(trip_time):
        empty_time_ratio = pickup_time / (pickup_time + trip_time)
        print(f"\n5. 平均空驶时间占比 (基于健康订单): {empty_time_ratio*100:.2f}%")
        if empty_time_ratio > 0.4:
            print("   [优化建议]: 空驶占比偏高。接驾时间与实际行程时间相近。可能原因：")
            print("   a. 派单半径虽然限制了，但路网严重拥堵导致实际开过去极其耗时。")
            print("   b. MCF 重平衡调度把大量车发去了错误的地方，导致它们还在路上跑，局部依然缺车。")
    else:
        print("\n5. 平均空驶时间占比: N/A")

    # 6. 重平衡执行情况 (V0.2)
    print("\n6. 重平衡执行情况 (V0.2 基于 MCF):")
    try:
        df_rebalance_logs = pd.read_sql_query("SELECT COUNT(*) as cnt FROM rebalance_logs", conn)
        rebalance_count = df_rebalance_logs['cnt'].iloc[0]
        print(f"   总共发起了 {rebalance_count} 次跨区域车辆重平衡调度。")
    except Exception:
        print("   暂无重平衡记录或表不存在。")

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
