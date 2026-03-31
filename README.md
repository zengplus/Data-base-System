# Taxis Information Database System (智能出租车调度仿真系统)

## 项目简介
本项目是一个基于 SUMO 交通仿真引擎与 Python 构建的**智能网约车/出租车调度与仿真系统**。
它模拟了真实的城市路网交通流（包含大量随机游走的背景车辆），并实现了一个完整的出租车派单、调度、重平衡和状态流转的闭环系统。

核心功能与特色：
- **实时交通仿真**：通过 SUMO 模拟包含复杂路网、红绿灯、真实拥堵车流的物理世界。
- **智能 KNN 调度与硬性限制**：使用 R-Tree 空间索引和 K-Nearest Neighbors 算法，在发生订单时，寻找最近且可达的空闲出租车进行派单，并辅以严格的接驾距离与绕路限制。
- **动态状态流转与可视化**：出租车根据任务状态（IDLE 绿 / PICKUP 橙 / OCCUPIED 红）在 SUMO GUI 中实时改变颜色。
- **基于真实地理信息的重平衡**：集成 `GeoPandas` 与真实的城市区域 Shapefile 文件，实时计算各区域供需差（Gap = Demand - Supply），动态将空车调度至高需求热点区域。
- **持久化数据与指标评估**：通过 SQLite 数据库实时记录订单状态、车辆位置和调度历史，并提供专属脚本一键生成核心业务指标（完成率、AWT、接驾时间、空驶率等）及可视化图表。

---

## 系统架构与核心模块

为严格满足本项目在时空数据管理和自主出租车调度上的目标，系统架构设计参考了经典的网约车仿真模型思路，并严格按照五大核心任务划分为以下模块，外加驱动整个仿真的主循环引擎：

### 0. 主循环引擎 (Main Simulation Engine)
- **模块位置**: `main.py`
- **功能职责**: 
  - 驱动 SUMO 仿真步进（Step by Step）。
  - **全天候车辆保活机制**：监听车辆位置与状态，防止空闲车辆到达终点被删除；对于因严重拥堵碰撞而掉线的车辆，提供即时掉线恢复与订单释放机制，确保全场 300 辆出租车在 1 小时仿真内永不减少。
  - 作为调度器的宿主，周期性触发订单生成、派单尝试和全局重平衡。

### 1. 空间索引设计 (Index Design)
- **模块位置**: `database/db_manager.py` 与 `database/rtree_index.py`
- **功能职责**: 
  - 在 SQLite 中利用 R-Tree 建立空间索引，存储并快速检索出租车的移动坐标 (x, y)。
  - 在每个 TraCI 仿真步，实时更新 300 辆出租车的最新物理位置。
  - 为下游的调度系统提供极速的空间范围 KNN 查询支持。

### 2. 订单请求处理 (Request Handling)
- **模块位置**: `dispatch/request_handler.py`
- **功能职责**: 
  - 随机生成 1,500 个乘客出行请求（Trip Requests）。
  - **时空动态分布**：订单生成在时间上呈现缓慢增长趋势（使用幂函数），在空间上呈现向城市中心聚拢的特征。
  - **连通性校验**：在生成订单时，强制校验起终点的物理距离（300m~1500m）与路网连通性，防止生成无法到达的“死单”。

### 3. 核心派单逻辑 (Dispatch Logic)
- **模块位置**: `dispatch/scheduler.py` & `simulation/route_planner.py`
- **功能职责**: 
  - 结合 KNN 查询结果与真实路网连通性，将订单分配给最优的出租车。
  - **严格派单限制**：如果最近的车距离乘客超过 1.5 公里（或绕路超过 30 条街），系统宁可让乘客等待，也坚决不派远距离车辆，从而彻底解决接驾时间（Pickup Time）虚高的问题。
  - **拥堵超时熔断机制**：为 `PENDING`（等待接单）和 `ASSIGNED`（接驾中）的订单设置 10 分钟超时限制。如果接单车辆卡死在严重拥堵路段无法到达，系统会自动取消死单并释放车辆。

### 4. 状态与可用性管理 (Availability Management)
- **模块位置**: `database/db_manager.py` (事务控制) & `dispatch/scheduler.py` (状态流转)
- **功能职责**: 
  - 使用数据库的**原子事务（Atomic Transactions）**严格管理出租车的生命周期状态。
  - 实现标准的状态流转与 GUI 颜色可视化联动：
    - `IDLE` (空闲/绿色) → `PICKUP` (接驾中/橙色) → `OCCUPIED` (载客中/红色) → `IDLE`。
  - 确保高并发派单时不会出现同一辆车被分配多次的数据一致性问题。

### 5. 空车重平衡调度 (Rebalancing)
- **模块位置**: `rebalance/rebalancer.py`
- **功能职责**: 
  - 周期性分析系统供需关系。
  - **真实不规则区域映射**：使用 `GeoPandas` 加载 `taxi_zones.shp`，将车辆坐标精确映射至真实城市的不规则多边形区域（若缺失文件则优雅降级为网格模式）。
  - **限制性智能调度**：查询数据库中的供需差，主动将闲置的空车调度至高需求区域。严格限制重平衡车辆最多不超过空闲车队的 20%，且调度距离不超过 2 公里，防止重平衡“抽干”系统运力。

### 6. 指标评估模块 (Performance Evaluation)
- **模块位置**: `evaluate_metrics.py`
- **功能职责**: 
  - 在仿真结束后或任意时刻，通过查询 `dispatch.db` 输出核心 KPI。
  - 核心指标包括：
    - 平均乘客等待时间（Average Wait Time, AWT）
    - 平均接驾时间（Pickup Time）
    - 订单完成率（Completion Rate）
    - 空驶率代理指标（Empty-Time Ratio）
  - 自动生成并保存订单状态分布的饼图 (`trip_status_distribution.png`)。

---

## 项目结构
```
.
├── main.py                     # 仿真系统主入口（负责循环驱动与车辆保活）
├── config.py                   # 全局参数配置（如车辆数、订单数、文件路径等）
├── schema.sql                  # SQLite 数据库表结构定义
├── evaluate_metrics.py         # 仿真结果评价指标与可视化脚本
├── database/                   # 数据库与空间索引模块
│   ├── db_manager.py           # SQLite 事务与状态管理
│   └── rtree_index.py          # R-Tree 空间索引与 KNN 查询
├── dispatch/                   # 订单调度与分配模块
│   ├── request_handler.py      # 订单时空动态生成器
│   └── scheduler.py            # 派单限制、状态流转与超时处理
├── rebalance/                  # 空车重平衡调度模块
│   └── rebalancer.py           # 基于 GeoPandas 的供需差调度
├── simulation/                 # SUMO 接口与路由规划模块
│   ├── route_planner.py        # A* 路由与连通性规划
│   └── sumo_connector.py       # TraCI 接口封装
├── data/                       # 真实地理与预计算数据
│   ├── pre_cal/                # 中心边映射等预处理数据
│   └── taxi_zones/             # 城市区域划分 Shapefile 文件
├── sumo_inputs/                # SUMO 仿真配置文件
│   ├── convert-1.net.xml       # 城市路网文件
│   ├── routes.rou.xml          # 出租车与背景车初始化路线
│   ├── sumo.sumocfg            # SUMO 引擎主配置
│   └── gui-settings.xml        # GUI 渲染与颜色配置
├── uv.lock / requirements.txt  # Python 依赖管理文件
└── README.md                   # 项目说明文档
```

---

## 使用说明

### 1. 操作系统要求
*   **推荐系统**：Ubuntu 20.04 LTS 或 Ubuntu 22.04 LTS（本项目在 Linux 环境下验证通过）。
*   **说明**：SUMO 仿真软件在 Linux 环境下运行最为稳定，且依赖安装最为便捷。

### 2. 安装 SUMO 仿真软件
在 Ubuntu 终端中执行以下命令安装 SUMO 及其工具：

```bash
sudo add-apt-repository ppa:sumo/stable
sudo apt-get update
sudo apt-get install sumo sumo-tools sumo-doc
```

### 3. Python 环境与依赖管理

本项目使用了 `GeoPandas` 等处理地理空间数据的库，推荐使用 `uv` 或 `pip` 在虚拟环境中安装依赖。

```bash
# 创建并激活虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

*(主要依赖包括：`sumolib`, `traci`, `geopandas`, `shapely`, `pandas`, `matplotlib`, `rtree`)*

### 4. 运行仿真

在安装好依赖并激活虚拟环境后，确保删除旧的测试数据库，然后直接运行主程序即可启动带 GUI 的可视化仿真：

```bash
# 清理旧数据库（如果是首次运行可忽略）
rm dispatch.db

# 启动仿真
python3 main.py
```
> **提示**：运行后会弹出 SUMO GUI 窗口。点击界面上方的绿色 "Play" 按钮即可开始观察仿真。你会看到：
> - 绿色的空闲出租车（IDLE）在接到订单后变橙色（PICKUP）。
> - 接上乘客后变红色（OCCUPIED），送达后重新变绿。
> - 大量黄色的背景车在路网中模拟真实交通拥堵。

### 5. 评估仿真结果

在仿真运行结束（或在运行过程中新开一个终端），运行指标评估脚本以查看系统表现：

```bash
python3 evaluate_metrics.py
```
终端将输出包括 AWT、接驾时间、完成率在内的核心数据，并在项目根目录生成饼图 `trip_status_distribution.png`。
