-- 项目B：sumo_to_db.sql
DROP TABLE IF EXISTS trips;
DROP TABLE IF EXISTS simulation_tasks; -- 空表
DROP TABLE IF EXISTS vehicle_trajectories;

-- 1. 记录完整的车辆行程 - 项目B运行为记录表
CREATE TABLE trips (
    trip_id INTEGER PRIMARY KEY AUTOINCREMENT, -- 行程唯一标识（主键）
    vehicle_id TEXT, -- 车辆ID
    pickup_datetime TEXT, -- 仿真开始步数（以时间格式存储）
    dropoff_datetime TEXT, -- 仿真结束步数（以时间格式存储）
    pickup_edge TEXT, -- 起始位置（路网边ID）
    dropoff_edge TEXT, -- 结束位置（路网边ID）
    trip_distance REAL, -- 仿真过程中行驶的总距离
    max_speed REAL, -- 最高行驶速度
    avg_speed REAL -- 平均行驶速度
);

-- 2. 仿真出租车里面订单任务的执行状态 - 项目B运行时为空表
CREATE TABLE simulation_tasks (
    task_id INTEGER PRIMARY KEY AUTOINCREMENT, -- 任务唯一标识（主键）
    dispatch_time TEXT, -- 派单请求时间
    origin_edge TEXT, -- 任务起始位置（路网边ID）
    dest_edge TEXT, -- 任务目的位置（路网边ID）
    status TEXT -- 任务状态（待执行PENDING/接驾PICKUP/完成COMPLETED）
);

-- 3. 记录车辆在仿真过程中的轨迹状态
CREATE TABLE vehicle_trajectories (
    traj_id INTEGER PRIMARY KEY AUTOINCREMENT, -- 轨迹记录唯一标识（主键）
    step INTEGER, -- 仿真步数
    vehicle_id TEXT, -- 车辆ID
    edge_id TEXT, -- 车辆所在路网边ID
    x REAL, -- 车辆横坐标
    y REAL, -- 车辆纵坐标
    speed REAL, -- 车辆当前速度
    distance_from_start REAL -- 车辆距行程起点的距离
);