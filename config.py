import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(BASE_DIR)

DB_FILE = os.path.join(BASE_DIR, "dispatch.db")
NET_FILE = os.path.join(BASE_DIR, "sumo_inputs", "convert-1.net.xml")
SQL_FILE = os.path.join(BASE_DIR, "schema.sql")
ROUTE_FILE = os.path.join(BASE_DIR, "sumo_inputs", "routes.rou.xml")
CFG_FILE = os.path.join(BASE_DIR, "sumo_inputs", "sumo.sumocfg")

# SUMO 仿真配置
GUI_ENABLED = True  # 设置为 True 以启动 sumo-gui，设置为 False 以启动命令行 sumo
BACKGROUND_VEH_COUNT = 2000
TAXI_COUNT = 300
REQUEST_COUNT = 1500
SIM_END = 3600
STEPS = SIM_END
DELAY = "0"

# 重平衡相关
REBALANCE_INTERVAL = 60        # 秒
GRID_SIZE = 10                  # 将路网划分为 GRID_SIZE x GRID_SIZE 个区域
