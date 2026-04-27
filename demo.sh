#!/bin/bash
# ===
# 自动驾驶出租车调度系统 - 演示版启动脚本
# ===
# 这个脚本专门用于课堂或会议展示 (Demo)。
# 它会强制开启 SUMO GUI，并配置适量的车辆，以便在屏幕上呈现出清晰、酷炫的视觉效果。
# ===

# 设置 Demo 专用的参数
export DEMO_MODE="1"
export GUI_ENABLED="1"            # 强制开启 GUI 进行可视化展示
export EXPERIMENT_MODE="proposed" # 默认展示最核心的 Proposed (完整) 系统
export TAXI_COUNT="150"           # 出租车数量 (适中，方便观察重平衡)
export BACKGROUND_VEH_COUNT="300" # 背景车数量 (制造拥堵，但不至于卡顿)
export REQUEST_COUNT="200"        # 订单数量
export SIM_END="600"              # 演示时长 10 分钟
export SUMO_SEED="42"             # 固定种子，确保每次演示效果一致
export PYTHON_RANDOM_SEED="42"

echo "==="
echo "启动自动驾驶出租车时空调度系统 - 实时演示模式"
echo "==="
echo "当前模式: $EXPERIMENT_MODE (包含 R-Tree KNN 派单 + 动态再平衡)"
echo "出租车数量: $TAXI_COUNT"
echo "背景车数量: $BACKGROUND_VEH_COUNT"
echo "==="

# 1. 首先生成演示专用的路网车辆文件
echo "[1/2] 正在生成带有出租车与背景车的初始路网文件..."
.venv/bin/python fix_routes_routing.py --taxis $TAXI_COUNT --bg $BACKGROUND_VEH_COUNT --seed $SUMO_SEED

# 2. 启动主控制程序 (带 GUI)
echo "[2/2] 正在连接 SUMO 并启动调度系统..."
echo "请在弹出的 SUMO 窗口中点击顶部的 'Play' (绿色三角形) 按钮开始演示！"
echo "建议在 SUMO 中将 Delay (延迟) 设置为 50-100ms，以便看清车辆状态变化。"
echo "==="

# 启动 main.py
.venv/bin/python main.py

echo "==="
echo "演示结束。"
echo "如需查看刚刚的运行指标，请查看终端输出或 SQLite 数据库。"
echo "==="
