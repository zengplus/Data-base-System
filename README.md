

# 基于 R-Tree 空间索引的自动驾驶出租车时空调度系统

[![SUMO](https://img.shields.io/badge/Simulator-SUMO%201.20.0-blue)]()
[![Python](https://img.shields.io/badge/Python-3.8%2B-green)]()
[![License](https://img.shields.io/badge/License-MIT-yellow)]()


## 项目简介

本项目为对应文章的**完整可复现实现**，包含：
- SQLite R‑Tree 空间索引构建与高并发 KNN 派单
- 动态供需再平衡策略（阈值触发 + 最小费用流调度）
- 原子事务状态管理（IDLE → PICKUP → OCCUPIED → REBALANCING）
- SUMO 高保真仿真（3014 边曼哈顿路网、2000 背景车、1500 潮汐请求）
- 9 组对照实验自动执行与论文图表生成

**核心结论**：在 300 辆出租车规模下，系统派单成功率 62.0%，平均等待时间 195.1 s，同时将空车闲置率从 83.7% **大幅压降至 31.3%**，以约 23% 的空驶里程代价实现了全局供需匹配。

---
## 演示效果

![系统演示](docs/demo/demo.gif)

*SUMO 仿真中的出租车调度过程：车辆状态颜色变化（绿-空闲，黄-接驾，红-载客，蓝-再平衡）*

---
## 核心需求

严格按照需求设计，每一项均有对应模块支撑：

| 要求项 | 实现项 |
| :--- | :--- |
| **索引设计** | SQLite R-Tree 虚拟表存储车辆实时坐标，TraCI 高频更新 |
| **请求处理** | 随机生成 1500 个请求，KNN 查询空闲车辆（LIMIT 15） |
| **派单逻辑** | 控制器通过 TraCI 最短路径接口计算真实路网接驾时间 |
| **状态管理** | 显式事务保证状态转换原子性，防止并发派单冲突 |
| **再平衡** | 30 s 周期统计网格供需差，调拨富余区 ≤20% 的空闲车 |
| **评估规模** | 3km×3km 路网（3014 有效边）、2000 背景车、300 出租车、3600 s 仿真 |

---

## 快速开始

### 环境要求

- SUMO ≥ 1.20.0

- Python ≥ 3.8

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行一次仿真
```bash
python main.py
```
默认使用 300 辆出租车，3000 s 仿真。可在 `config.py` 中调整参数。

### 批量复现论文全部实验
```bash
python run_experiments.py \
    --modes baseline knn proposed \
    --fleet-sizes 100 200 300 \
    --request-count 1500 \
    --background-count 2000 \
    --sim-end 3600 \
    --seed 42
```
结果自动保存至 `experiment_results.csv`。

### 生成论文图表
进入 `docs/paper/`，运行 Jupyter Notebook `visualize_results.ipynb` 即可生成全部对比图表。

---

## 系统架构

```

┌─────────────┐ TraCI ┌─────────────┐

│ SUMO │ ◄──────────────► │ Python │

│ 仿真环境 │ │ 控制器 │

└─────────────┘ └──────┬──────┘

│ SQL

▼

┌─────────────┐

│ SQLite │

│ + R-Tree │

└─────────────┘

```

仿真主循环每 30 秒执行一次：同步状态 → 生成请求 → KNN 匹配 → 再平衡 → 推进仿真。

---

## 核心模块

### 1. R-Tree 空间索引
```sql
CREATE VIRTUAL TABLE taxi_locations USING rtree(
    id INTEGER,
    minX REAL, maxX REAL,
    minY REAL, maxY REAL
);
```
车辆移动时同步更新 R‑Tree 索引，KNN 查询复杂度 $O(\log N)$，排除全表扫描。

### 2. 动态再平衡
$$Gap(c) = D(c) - S(c)$$
当某网格单元缺口 $> \theta$（$\theta=5$）时，从富余区调拨不超过 20% 的 IDLE 车辆前往。调度车辆暂时标记为 `REBALANCING`，抵达后恢复 `IDLE`。

### 3. 原子状态事务
```sql
BEGIN TRANSACTION;
UPDATE taxis SET status='PICKUP' WHERE taxi_id=?;
UPDATE trip_requests SET status='ASSIGNED' WHERE request_id=?;
INSERT INTO assignments ... ;
COMMIT;
```
杜绝一车多派，保证高并发下的数据一致性。

### 4. 真实路网与潮汐背景
- 路网：曼哈顿 3km×3km，3014 条有效边
- 背景车：2000 辆，自定义 A* 路径，**惩罚穿越市中心**，制造真实拥堵梯度
- 需求：1500 个请求，80% 集中在中心热点区

---

##  实验结果速览

### 9 组实验核心数据

| 指标 | Baseline | 纯 KNN | **Proposed** |
| :--- | :--- | :--- | :--- |
| 成功率 ↑ | 19.3% | 64.0% | **62.0%** |
| 平均等待 ↓ | 323.6 s | 191.6 s | **195.1 s** |
| **空车率 ↓** | 76.7% | 83.7% | **31.3%** |
| 空驶率 | 52.3% | 15.1% | **38.6%** |

**Proposed** 以 23.5% 的额外空驶代价，消除了 52.4% 的闲置运力，实现了全局供需平衡。

> 可视化结果请见 `docs/paper/` 中的图表。

---

## 项目结构 

```
.
├── main.py                     # 单次仿真实验
├── run_experiments.py          # 批量仿真实验（9 组）
├── config.py                   # 全局参数
├── schema.sql                  # 数据库初始化
│
├── database/                   # 数据库与 R-Tree 操作
│   ├── db_manager.py
│   └── rtree_index.py
├── dispatch/                   # 请求生成、KNN 派单、调度器
│   ├── knn_finder.py
│   ├── request_generator.py
│   └── scheduler.py
├── rebalance/                  # 供需分析、再平衡执行
│   ├── supply_demand.py
│   └── rebalancer.py
├── simulation/                 # SUMO TraCI 接口
│   ├── sumo_connector.py
│   └── route_planner.py
├── vehicle/                    # 车辆状态机与状态更新
│   ├── state_machine.py
│   └── atomic_updater.py
├── sumo_inputs/                # SUMO 路网与车流配置
├── docs/paper/                 # 论文源码、图表生成
└── utils/                      # 辅助工具
```

