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

本项目严格按照 `项目要求.md` 中的目标进行设计，将系统划分为以下 5 大核心模块（对应要求中的 Detailed Tasks）以及 1 个主循环引擎模块。

### 0. 主循环引擎模块 (Main Engine)
- **文件映射**: `main.py`, `config.py`
- **功能描述**: 
  - 驱动整个 SUMO 仿真步进（Step）。
  - 监听所有车辆（2000辆背景车、300辆出租车），在其快到达终点时**提前无缝续接路线**，确保车辆无限循环行驶，不会消失。
  - 在每个时间步统筹调用底层的订单生成、调度、状态更新和重平衡模块。

### 1. 空间索引设计模块 (Index Design)
- **文件映射**: `database/rtree_index.py`
- **要求对应**: *Implement an R-Tree index in SQLite to store moving taxi coordinates (x, y) updated via TraCI.*
- **功能描述**: 
  - 实现了基于 R-Tree 的空间索引。
  - 每一帧通过 TraCI 获取所有出租车的最新 (x,y) 坐标，并将其更新到数据库和 R-Tree 内存树中，极大地提升了后续空间查询的速度。

### 2. 订单生成与处理模块 (Request Handling)
- **文件映射**: `dispatch/request_generator.py`
- **要求对应**: *Generate stochastic passenger trip requests; use a K-Nearest Neighbor (KNN) query to find the closest idle taxis.*
- **功能描述**: 
  - 采用泊松分布等随机策略，在仿真的 3600 秒内生成总计约 1500 个乘客出行订单（Trip Requests）。
  - 在接单阶段，利用第 1 模块构建的 R-Tree 索引执行 **KNN (K=20) 查询**，快速筛选出距离乘客最近的空闲出租车候选池。

### 3. 智能派单与路由模块 (Dispatch Logic)
- **文件映射**: `dispatch/scheduler.py`, `simulation/route_planner.py`
- **要求对应**: *Write a Python controller that assigns the taxi in the DB and uses TraCI’s setRoute to navigate to the passenger.*
- **功能描述**: 
  - **Python 控制器**：负责将候选池中的车辆进行连通性验证（排除死胡同或单行道阻碍）。
  - **数据库分配**：选定最优车辆后，在数据库中写入分配记录（Assignment）。
  - **SUMO 导航**：通过 TraCI 的 `setRoute` 接口，为接单出租车规划一条前往乘客上车点的最短可达路径。

### 4. 车辆可用性与状态管理模块 (Availability Management)
- **文件映射**: `database/db_manager.py`, `dispatch/scheduler.py`
- **要求对应**: *Use atomic transactions to update taxi status from IDLE to PICKUP to OCCUPIED.*
- **功能描述**: 
  - **原子事务**：使用 SQLite 事务机制，确保车辆状态与订单状态的更新是原子的，防止“一车多派”或数据不一致。
  - **状态流转机制**：
    - `IDLE` (绿色)：空闲巡游状态。
    - `PICKUP` (橙色)：接单后前往上车点的状态。
    - `OCCUPIED` (红色)：接到乘客，前往目的地的载客状态。
  - 状态变化时，不仅更新数据库，同时调用 TraCI 同步改变 SUMO GUI 中的车辆颜色。

### 5. 空车重平衡模块 (Rebalancing)
- **文件映射**: `rebalance/rebalancer.py`
- **要求对应**: *Periodically query the DB for areas with high request density but low taxi supply and "rebalance" empty taxis to those zones.*
- **功能描述**: 
  - 周期性（如每 60 秒）执行全局扫描。
  - 查询数据库中“未接单（PENDING）请求密集”但“周边缺乏 IDLE 车辆”的供需失衡区域（热点区）。
  - 提取远离热点区的空闲车辆，强制下发重平衡指令，调度它们驶向需求高地，从而降低全局的乘客平均等待时间（AWT）和空载率。

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

