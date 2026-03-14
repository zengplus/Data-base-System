# Taxis Information Database System

## 项目简介
项目分为 Project A 和 Project B 两个不同的项目：
- Project A：作为仿真输入源，核心存储出租车真实运营的原始记录；
- Project B：作为仿真输出端，核心记录仿真过程中车辆的轨迹数据。

---

## 数据库思路

1.  trips 表：
    *   记录完整的车辆行程；

2.  simulation_tasks 表：
    *   仿真出租车里面订单任务的执行状态；
    *   Project A (Input)：作为仿真任务队列，存储从出租车原始数据提取的派单请求；
    *   Project B (Output)：项目运行是空白，没有实际存储数据，后期根据需要进行优化；

3.  vehicle_trajectories 表：
    *   记录车辆在仿真过程中的轨迹状态；
    *   Project B 独有：仿真输出的核心高频数据，仅实现基础存储功能，未做优化；

---

### Project A：输入型数据库（仿真任务数据源）
#### 设计背景
仿真需从出租车历史数据中筛选有效订单生成仿真任务，核心问题是全量表查询效率低，因此设计核心为优化读性能、适配数据筛选需求。

## 项目优化方向
确定基于 Project A 还是 Project B 以后，对数据库进行优化。

---

## AI 辅助声明
项目编写是基于 Trae IDE（类VS Code的ide）完成的编写代码活动，使用该IDE内置的Ai Auto自动模型提供AI辅助能力，相关辅助行为及对应代码补全在代码中的注释体现。

## 项目结构
```
.
├── data/                       # 原始数据目录
│   └── 24hour_end_1.csv        
├── sumo_inputs/                # SUMO 仿真输入与配置文件
│   ├── convert-1.net.xml       
│   ├── routes.rou.xml          
│   ├── sumo.sumocfg            
│   └── ...                     
├── docs/                       # 项目文档与学习记录
│   └── study/                  # 数据库课程学习笔记
├── csv_to_db.py                # [Project A] 将 CSV 原始数据导入 SQLite 数据库
├── db_to_sumo.py               # [Project A] 读取数据库生成 SUMO 仿真路由文件
├── db_to_sumo.sql              # [Project A] 相关的 SQL 建表语句
├── sumo_to_db.py               # [Project B] 运行 SUMO 仿真并将轨迹数据存入数据库
├── sumo_to_db.sql              # [Project B] 相关的 SQL 建表语句
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

### 4. 依赖列表 (requirements.txt)
项目根目录下已创建 `requirements.txt`，主要包含：
*   `traci`: SUMO 的 Python 接口库
*   `sumolib`: SUMO 的网络与工具库
