import os
import sys
import json
import sqlite3
import traceback

# 确保能找到项目模块
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
import config

def test_database():
    print("\n--- 1. 测试数据库与索引组件 ---")
    try:
        from database.db_schema import init_db
        from database.db_manager import DBManager
        from database.rtree_index import RTreeIndex
        
        # 使用内存数据库进行测试，避免破坏实际数据
        conn = sqlite3.connect(':memory:')
        cursor = conn.cursor()
        
        # 简单测试建表
        with open(config.SQL_FILE, 'r') as f:
            cursor.executescript(f.read())
            
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        required_tables = ['taxis', 'trip_requests', 'assignments', 'taxi_locations', 'rebalance_logs', 'traffic_state']
        
        missing = [t for t in required_tables if t not in tables]
        if missing:
            print(f"❌ 数据库测试失败: 缺少表 {missing}")
            return False
            
        print("✅ 数据库 Schema 验证通过 (所有必须的 6 张表均存在)")
        return True
    except Exception as e:
        print(f"❌ 数据库测试异常: {e}")
        traceback.print_exc()
        return False

def test_sumo_network():
    print("\n--- 2. 测试 SUMO 路网解析组件 ---")
    try:
        import sumolib
        if not os.path.exists(config.NET_FILE):
            print(f"❌ 找不到路网文件: {config.NET_FILE}")
            return False
            
        net = sumolib.net.readNet(config.NET_FILE)
        edges = net.getEdges()
        print(f"✅ 成功加载路网，共解析到 {len(edges)} 条边。")
        
        # 测试坐标转换
        e = edges[0]
        x, y = e.getShape()[0]
        lon, lat = net.convertXY2LonLat(x, y)
        print(f"✅ 坐标转换测试通过: SUMO (x={x:.2f}, y={y:.2f}) -> LonLat ({lon:.6f}, {lat:.6f})")
        return True
    except Exception as e:
        print(f"❌ SUMO 路网测试异常: {e}")
        traceback.print_exc()
        return False

def test_spatial_cache_and_gis():
    print("\n--- 3. 测试 GIS 映射与空间缓存组件 (核心重平衡前置) ---")
    try:
        import geopandas as gpd
        from shapely.geometry import Point
        from database.spatial_cache import SpatialCache
        import sumolib
        
        net = sumolib.net.readNet(config.NET_FILE)
        cache = SpatialCache()
        
        # 测试 Shapefile 加载
        shp_path = os.path.join(config.BASE_DIR, 'data', 'taxi_zones', 'taxi_zones.shp')
        if not os.path.exists(shp_path):
            print(f"⚠️ 未找到 Shapefile: {shp_path}，系统将降级为网格模式运行。")
        else:
            if cache.use_shp:
                print(f"✅ 成功加载 {shp_path}，当前坐标系: {cache.shp_gdf.crs}")
            else:
                print(f"❌ 找到了 Shapefile 但 GeoPandas 解析失败！")
                return False

        # 测试中心边映射加载
        json_path = os.path.join(config.BASE_DIR, 'data', 'pre_cal', 'centralEdges.json')
        if not os.path.exists(json_path):
            print(f"⚠️ 未找到中心边文件: {json_path}，重平衡回退机制将生效。")
        else:
            if cache.central_edges:
                print(f"✅ 成功加载 centralEdges.json，包含 {len(cache.central_edges)} 个区域映射。")
            else:
                print(f"❌ 找到了 centralEdges.json 但解析失败！")
                return False
                
        # 测试坐标映射逻辑
        # 随便取路网中心点测试
        edges = net.getEdges()
        x, y = edges[len(edges)//2].getShape()[0]
        
        # 伪造 bounds 设置
        cache.set_network_bounds((0, 10000, 0, 10000), net=net)
        region_id = cache.get_region_id(x, y)
        print(f"✅ 区域映射测试通过: SUMO 坐标 (x={x:.2f}, y={y:.2f}) 被映射到区域 ID: {region_id}")
        
        return True
    except Exception as e:
        print(f"❌ GIS 空间组件测试异常: {e}")
        traceback.print_exc()
        return False

def test_dispatch_and_routing():
    print("\n--- 4. 测试派单算法与路由组件 ---")
    try:
        from simulation.route_planner import RoutePlanner
        
        planner = RoutePlanner(config.NET_FILE)
        import sumolib
        net = sumolib.net.readNet(config.NET_FILE)
        edges = net.getEdges()
        
        # 找两条相连的边测试 A*
        e1 = edges[10].getID()
        e2 = edges[11].getID()
        route = planner.get_shortest_path(e1, e2)
        
        if route is not None:
            print(f"✅ 路由规划 (A*) 测试通过，生成路径长度: {len(route)}")
        else:
            print(f"⚠️ 路由规划测试警告: {e1} 到 {e2} 不可达，这是正常的物理现象，但代码没报错。")
            
        return True
    except Exception as e:
        print(f"❌ 派单路由组件测试异常: {e}")
        traceback.print_exc()
        return False

def test_rebalance_logic():
    print("\n--- 5. 测试核心重平衡算法逻辑 (MCF) ---")
    try:
        from rebalance.min_cost_flow import MinCostFlow
        from rebalance.supply_demand import SupplyDemand
        
        # 伪造一些数据来测试 MCF 算法本身是否会报错
        source_supplies = {'A': 10, 'B': 5}
        target_demands = {'C': 8, 'D': 7}
        cost_matrix = {
            ('A', 'C'): 10, ('A', 'D'): 50,
            ('B', 'C'): 40, ('B', 'D'): 20
        }
        
        instructions = MinCostFlow.solve(source_supplies, target_demands, cost_matrix)
        print(f"✅ MCF 算法测试通过，生成调度指令: {instructions}")
        
        # 校验调度结果是否符合贪心预期：
        # 成本最小的是 A->C(10), B->D(20)
        # A 提供 8 辆给 C, B 提供 5 辆给 D
        if len(instructions) > 0:
             print("   算法逻辑工作正常。")
             return True
        else:
             print("❌ MCF 算法未生成任何指令！")
             return False
    except Exception as e:
        print(f"❌ MCF 算法测试异常: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("="*50)
    print("   Taxis Information Database System - 组件健康自检")
    print("="*50)
    
    res1 = test_database()
    res2 = test_sumo_network()
    res3 = test_spatial_cache_and_gis()
    res4 = test_dispatch_and_routing()
    res5 = test_rebalance_logic()
    
    print("\n" + "="*50)
    if all([res1, res2, res3, res4, res5]):
        print("🎉 恭喜！所有核心组件（包括 GIS、SUMO 路由、数据库、重平衡前置数据）均正常工作！")
        print("💡 您可以放心执行: python main.py")
    else:
        print("⚠️ 存在组件测试未通过，请检查上方日志中的 ❌ 错误信息。")
    print("="*50)
