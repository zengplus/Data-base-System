import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(BASE_DIR)

DB_FILE = os.path.join(BASE_DIR, "dispatch.db")
NET_FILE = os.path.join(BASE_DIR, "sumo_inputs", "convert-1.net.xml")
SQL_FILE = os.path.join(BASE_DIR, "schema.sql")
ROUTE_FILE = os.path.join(BASE_DIR, "sumo_inputs", "routes.rou.xml")
CFG_FILE = os.path.join(BASE_DIR, "sumo_inputs", "sumo.sumocfg")

def _get_env_int(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default

def _get_env_str(name, default):
    value = os.getenv(name)
    return value if value is not None else default

def _get_env_bool(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}

# SUMO 仿真配置
GUI_ENABLED = _get_env_bool("GUI_ENABLED", True)  # True 启动 sumo-gui，False 启动 sumo
BACKGROUND_VEH_COUNT = _get_env_int("BACKGROUND_VEH_COUNT", 2000)
TAXI_COUNT = _get_env_int("TAXI_COUNT", 300)
REQUEST_COUNT = _get_env_int("REQUEST_COUNT", 1500)
SIM_END = _get_env_int("SIM_END", 3600)
ENABLE_TAXI_REVIVE = _get_env_bool("ENABLE_TAXI_REVIVE", True)
STEPS = SIM_END
DELAY = _get_env_str("SUMO_DELAY", "0")
SUMO_SEED = _get_env_int("SUMO_SEED", 42)
PYTHON_RANDOM_SEED = _get_env_int("PYTHON_RANDOM_SEED", 42)

# 实验模式：baseline / knn / proposed
EXPERIMENT_MODE = _get_env_str("EXPERIMENT_MODE", "proposed").strip().lower()

# 重平衡相关
REBALANCE_INTERVAL = _get_env_int("REBALANCE_INTERVAL", 30)  # 秒
GRID_SIZE = _get_env_int("GRID_SIZE", 10)  # 将路网划分为 GRID_SIZE x GRID_SIZE 个区域
