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

## 项目结构（数据库核心视角）
```
.
├── db/
│   ├── schema/
│   │   ├── project_a.sql       # 输入型数据库Schema（读优化）
│   │   ├── project_b.sql       # 输出型数据库Schema（写优化，未完善）
│   │   └── final_system.sql    # 最终优化后的统一Schema
│   ├── scripts/
│   │   ├── csv_to_db.py        # 出租车原始数据入库
│   │   ├── db_read_optim.py    # Project A 读性能测试脚本
│   │   └── db_write_optim.py   # Project B 写性能测试脚本
├── sumo/                       # 仿真辅助目录（验证数据库功能）
│   ├── db_to_sumo.py           # 数据库→仿真（读验证）
│   └── sumo_to_db.py           # 仿真→数据库（写验证）
├── data/                       # 原始数据目录
│   └── 24hour_end_1.csv
└── optimize/                   # 优化脚本目录
    ├── db_sync.py              # 读写分离同步脚本
    └── data_audit.py           # 数据校验与溯源脚本
```
