# Spatio-Temporal Autonomous Taxi Dispatching System

基于 SUMO 与 SQLite R-Tree 的大规模自动驾驶出租车时空调度系统。

本项目实现了一个完整且可扩展的自动驾驶出租车动态调度框架。针对城市高峰时段潮汐交通带来的供需空间失衡问题，本系统利用 R-Tree 空间索引实现了高效的 KNN 派单匹配，并设计了动态再平衡（Dynamic Rebalancing）策略，主动将空闲运力调度至热点区域，从而显著降低空车率，盘活全局运力。

## 🚀 项目亮点 (Key Features)

- **高效的空间索引**：使用 SQLite R-Tree 虚拟表，将 KNN 派单的匹配复杂度从 $O(N)$ 降至 $O(\log N)$，支持高并发派单。
- **动态车队再平衡 (Dynamic Rebalancing)**：主动监测区域供需缺口，动态抽调冗余车辆前往高需求区域，打破“贪心陷阱”，将局部高峰空车率从 `83.7%` 压降至 `31.3%`。
- **真实路网与背景车流**：基于真实纽约局部路网提取，并内置带 A* 惩罚启发式的背景车流逻辑，模拟逼真的城市潮汐拥堵。
- **一键式实验复现**：提供自动化测试与指标提取脚本，一键运行 9 组双变量对照实验（Baseline vs KNN vs Proposed，车队规模 100/200/300）。
- **完整的论文级分析**：包含配套的数据处理 Jupyter Notebook 和最终排版完成的 LaTeX 会议论文。

## 📂 项目结构 (Project Structure)

```text
.
├── main.py                  # 仿真系统的主入口，负责连接 SUMO 并启动调度主循环
├── config.py                # 全局配置参数（数据库路径、SUMO 配置等）
├── run_experiments.py       # 自动化实验脚本（一键跑 9 组实验并导出 CSV）
├── fix_routes_routing.py    # 动态路网与车队生成脚本（在每次实验前按参数生成 SUMO routes）
├── schema.sql               # SQLite 数据库表结构初始化文件（包含 R-Tree 索引）
├── experiment_results.csv   # 自动导出的 9 组实验核心指标结果表
├── requirements.txt         # Python 依赖项
├── LICENSE                  # 开源协议
├── data/                    # 静态数据目录（如 Taxi Zones shapefile）
├── database/                # 数据库交互封装模块
├── dispatch/                # 派单核心逻辑（KNN 查询、请求生成等）
├── rebalance/               # 动态再平衡模块（供需统计与跨区调度）
├── simulation/              # SUMO TraCI 交互接口与路网坐标转换
├── sumo_inputs/             # SUMO 核心配置文件 (.net.xml, .sumocfg 等)
├── vehicle/                 # 出租车与背景车状态机管理
└── docs/                    
    └── paper/               # 论文与实验可视化目录
        ├── paper_final.tex  # 最终排版完成的学术论文 (LaTeX)
        ├── visualize_results.ipynb # 实验数据处理与图表生成 Notebook
        └── fig_*.png        # 生成的核心对比图表
```

## 🛠️ 环境依赖与安装

1. **安装 SUMO (Simulation of Urban MObility)**
   - Ubuntu: `sudo apt install sumo sumo-tools sumo-doc`
   - MacOS: `brew install sumo`
2. **安装 Python 依赖**
   建议使用虚拟环境：
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

## 🧪 运行与测试

### 1. 单次常规运行
您可以直接运行主程序以查看实时仿真过程（可修改 `config.py` 开启 GUI）：
```bash
python main.py
```

### 2. 一键跑完 9 组对照实验（复现论文数据）
项目内置了用于学术评估的自动化实验脚本。该脚本会自动控制背景车、出租车数量，并进行 3 种策略的横向对比，最终将指标导出为 `experiment_results.csv`。
```bash
# 运行缩放版实验 (加快测试速度，比例结果不变)
python run_experiments.py --modes baseline knn proposed --fleet-sizes 100 200 300 --request-count 150 --background-count 300 --sim-end 600 --seed 42
```
*注：为了保证论文数据的绝对可复现性，脚本强制设定了随机种子 (`--seed 42`)*。

### 3. 实验数据可视化与论文
运行完实验后，请前往 `docs/paper/` 目录：
1. 打开 `visualize_results.ipynb`。
2. 该 Notebook 会读取刚生成的 CSV，输出 9 组独立实验对照表格。
3. 自动将结果等比例放大以符合 `3600s/1500 requests` 的项目标准，并生成所需的论文对比图表（完成率、等待时间、空车率）。
4. 编译 `paper_final.tex` 即可生成完整的中文会议论文。

## 📊 核心指标与论文成果

基于上述框架，系统在应对极端空间不平衡的潮汐请求时表现优异。在 300 辆车的规模下：
- **纯 KNN 策略**虽然能实现较短的局部响应时间，但由于“贪心陷阱”，大量车辆在边缘区域**闲置趴窝**，导致全局空车率高达 `83.7%`。
- **Proposed 完整系统**在保持同等响应时间（195.1秒）和高完成率（62.0%）的前提下，通过再平衡主动调度，成功将**空车率压降至 31.3%**，实现了全局运力的深度激活。

详细的学术分析请参考 `docs/paper/paper_final.tex`。

---
*Developed for Academic Research & Course Project.*
