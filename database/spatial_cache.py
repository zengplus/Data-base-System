import os
import json
import geopandas as gpd
from shapely.geometry import Point
import config

class SpatialCache:
    """网格与真实区域坐标映射、区域中心数据缓存"""
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(SpatialCache, cls).__new__(cls)
            cls._instance._init_cache()
        return cls._instance

    def _init_cache(self):
        self.shp_gdf = None
        self.use_shp = False
        self.central_edges = {}
        self.bounds = None
        self.cell_width = 0
        self.cell_height = 0
        self._region_cache = {}
        self.net = None # 保存 SUMO net 引用用于坐标转换

        # 尝试加载 Shapefile
        shp_path = os.path.join(config.BASE_DIR, 'data', 'taxi_zones', 'taxi_zones.shp')
        if os.path.exists(shp_path):
            try:
                self.shp_gdf = gpd.read_file(shp_path)
                # 曼哈顿的 taxi_zones.shp 通常是 EPSG:4326 或特定的投影
                if self.shp_gdf.crs is None or self.shp_gdf.crs.to_string() != 'EPSG:4326':
                     self.shp_gdf = self.shp_gdf.to_crs('EPSG:4326')
                self.use_shp = True
                print(f"[SpatialCache] 成功加载 {shp_path}，使用基于 Shapefile 的真实区域划分。")
            except Exception as e:
                print(f"[SpatialCache] Warning: Failed to load shapefile {shp_path}: {e}")
        else:
            print(f"[SpatialCache] 未找到 Shapefile，将降级使用网格划分。")

        # 尝试加载中心边映射
        json_path = os.path.join(config.BASE_DIR, 'data', 'pre_cal', 'centralEdges.json')
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r') as f:
                    raw_data = json.load(f)
                    for k, v in raw_data.items():
                        self.central_edges[int(k)] = str(v)
                print(f"[SpatialCache] 成功加载 centralEdges.json，包含 {len(self.central_edges)} 个区域的中心边。")
            except Exception as e:
                print(f"[SpatialCache] Warning: Failed to load centralEdges.json {json_path}: {e}")

    def set_network_bounds(self, bounds, net=None):
        """设置路网边界并初始化网格参数，同时传入 net 用于坐标转换"""
        self.bounds = bounds
        self.net = net
        if bounds:
            min_x, max_x, min_y, max_y = bounds
            self.cell_width = (max_x - min_x) / config.GRID_SIZE
            self.cell_height = (max_y - min_y) / config.GRID_SIZE

    def get_region_id(self, x, y):
        """获取坐标所在的宏观区域 ID: Center, Surrounding_A, Surrounding_B"""
        coord = (round(x, 2), round(y, 2))
        if coord in self._region_cache:
            return self._region_cache[coord]

        # 如果没有 bounds，给个默认值防止报错
        if not self.bounds:
            return "Center"

        min_x, max_x, min_y, max_y = self.bounds
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        
        # 定义中心区域的半径（比如路网宽度的一小半，形成一个小范围热点）
        radius_sq = ((max_x - min_x) * 0.25) ** 2
        
        dist_sq = (x - center_x)**2 + (y - center_y)**2
        
        if dist_sq <= radius_sq:
            region_id = "Center"
        else:
            # 如果不在中心，根据 x 坐标分东西两区
            if x > center_x:
                region_id = "Surrounding_A" # 东区
            else:
                region_id = "Surrounding_B" # 西区

        self._region_cache[coord] = region_id
        return region_id

    def get_central_edge(self, region_id):
        """由于使用了宏观区域，不再依赖具体的细分 central_edge，这里可以返回 None 让调度器走 Fallback，或者随机选取"""
        return None
