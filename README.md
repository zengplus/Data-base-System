# Taxis Information Database System (智能出租车调度仿真系统)

## 项目简介
本项目是一个基于 SUMO 交通仿真引擎与 Python 构建的**智能出租车调度与仿真系统**。
它模拟了真实的城市路网交通流（包含大量随机游走的背景车辆），并实现了一个完整的出租车派单、调度和状态流转的闭环系统。

核心功能包括：
- **实时交通仿真**：通过 SUMO 模拟包含网格路网、红绿灯、背景车流的真实物理世界。
- **智能 KNN 调度**：使用 R-Tree 空间索引和 K-Nearest Neighbors 算法，在发生订单时，寻找最近且可达的空闲出租车进行派单。
- **动态状态流转与可视化**：出租车根据任务状态（IDLE 绿 / PICKUP 橙 / OCCUPIED 红）在 SUMO GUI 中实时改变颜色。
- **持久化数据记录**：通过 SQLite 数据库实时记录订单状态、车辆位置和调度历史。

---

## 系统架构与核心模块

为严格满足本项目在时空数据管理和自主出租车调度上的目标，系统架构设计参考了经典的 `taxi-sim` 仿真模型思路（如供需计算与网格化路网调度），并严格按照五大核心任务划分为以下模块，外加驱动整个仿真的主循环引擎：

### 0. 主循环引擎 (Main Simulation Engine)
- **模块位置**: `main.py`
- **功能职责**: 
  - 驱动 SUMO 仿真步进（Step by Step）。
  - 监听车辆到达事件，实现所有车辆（背景车与出租车）的**无限循环行驶**（在到达终点前动态规划新路线），确保规模稳定的交通流。
  - 作为调度器的宿主，周期性触发订单生成、派单尝试和全局重平衡。

### 1. 空间索引设计 (Index Design)
- **模块位置**: `database/db_manager.py` (包含 R-Tree 与 SQLite 集成)
- **功能职责**: 
  - 核心要求：在 SQLite 中利用 R-Tree（或基于网格的替代方案）建立空间索引，存储并快速检索出租车的移动坐标 (x, y)。
  - 在每个 TraCI 仿真步，实时更新 300 辆出租车的最新物理位置。
  - 为下游的调度系统提供极速的空间范围查询支持。

### 2. 订单请求处理 (Request Handling)
- **模块位置**: `main.py` (随机请求生成) & `database/db_manager.py` (KNN 查询)
- **功能职责**: 
  - 随机生成 1,500 个分布在 3km × 3km 城市网格中的乘客出行请求（Trip Requests）。
  - 利用数据库的空间索引执行 **K-Nearest Neighbor (KNN) 查询**，快速定位离乘客出发点最近的空闲出租车（Idle Taxis）集合。

### 3. 核心派单逻辑 (Dispatch Logic)
- **模块位置**: `dispatch/scheduler.py` & `simulation/route_planner.py`
- **功能职责**: 
  - 结合 KNN 查询结果与真实路网连通性，将订单分配给最优的出租车。
  - 使用 Python 控制器调用 TraCI 的 `setRoute` 接口，规划并下发导航路线，指挥出租车穿越背景车流前往接驾点。
  - 确保车辆在复杂的城市路网（>500 条边）中成功抵达目的地。

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
  - 周期性（如每 5 分钟）分析系统供需关系。
  - 借鉴 `taxi-sim` 的网格化评估思路，查询数据库中“订单请求密度高但空闲车辆供给低”的热点区域。
  - 主动将长时间闲置的空闲出租车调度至这些高需求区域，从而有效降低乘客的平均等待时间（AWT）并优化空驶率。

### 6. 指标评估模块 (Performance Evaluation)
- **模块位置**: `evaluate_metrics.py`
- **功能职责**: 
  - 在仿真结束后，通过查询 `dispatch.db` 输出核心 KPI。
  - 计算平均乘客等待时间（Average Wait Time, AWT）、行程时间、订单完成率。
  - 后续可用于分析空间索引深度、车队密度与派单成功率的关联。

---

## AI 辅助声明
项目编写是基于 Trae IDE（类VS Code的ide）完成的编写代码活动，使用该IDE内置的Ai Auto自动模型提供AI辅助能力，相关辅助行为及对应代码补全在代码中的注释体现。

## 项目结构
```
.
├── main.py                     # 仿真系统主入口
├── config.py                   # 全局参数配置（步数、概率、文件路径）
├── schema.sql                  # 数据库表结构定义
├── dispatch.db                 # 运行时生成的 SQLite 数据库
├── database/                   # 数据库交互模块
├── dispatch/                   # 订单调度与分配模块
├── rebalance/                  # 空车重平衡调度模块
├── simulation/                 # SUMO 接口与路由规划模块
├── sumo_inputs/                # SUMO 仿真配置文件
│   ├── convert-1.net.xml       # 路网文件
│   ├── routes.rou.xml          # 车辆路线与定义文件
│   ├── sumo.sumocfg            # SUMO 主配置
│   └── gui-settings.xml        # GUI 渲染与颜色配置
├── docs/                       # 项目文档与学习记录
├── requirements.txt            # Python 依赖列表
└── README.md                   # 项目说明文档
```

---

## 使用说明

### 1. 操作系统要求
*   **推荐系统**：Ubuntu 20.04 LTS 或 Ubuntu 22.04 LTS。
*   **说明**：SUMO 仿真软件在 Linux 环境下运行最为稳定，且安装最为便捷。

### 2. 安装 SUMO 仿真软件
在 Ubuntu 终端中执行以下命令安装 SUMO 及其工具：

```bash
sudo add-apt-repository ppa:sumo/stable
sudo apt-get update
sudo apt-get install sumo sumo-tools sumo-doc
```

### 3. Python 环境与依赖管理

本项目推荐使用 `uv` 进行依赖管理，因为它速度极快且生成的 `uv.lock` 文件能确保依赖版本的严格一致。

#### 方式一：使用 uv


1.  **安装 uv**:
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source $HOME/.local/bin/env  # 使命令生效
    ```

2.  **创建虚拟环境并安装依赖**:
    ```bash
    # 在项目根目录下执行
    uv venv 
    source .venv/bin/activate
    uv pip sync uv.lock
    ```

#### 方式二：使用标准 pip

如果你不想安装额外的工具，也可以使用标准的 `pip`：

```bash
pip install -r requirements.txt
```

### 4. 运行仿真

在安装好依赖并激活虚拟环境后，在项目根目录下直接运行主程序即可启动带 GUI 的可视化仿真：

```bash
python3 main.py
```
> **提示**：运行后会弹出 SUMO GUI 窗口。点击界面上方的绿色 "Play" 按钮即可开始观察仿真。你会看到绿色的空闲出租车在接到订单后变橙色，接上乘客后变红色，送达后重新变绿。

