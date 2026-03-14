-- 项目A：输入型数据库表结构
DROP TABLE IF EXISTS trips;
DROP TABLE IF EXISTS simulation_tasks;

-- 1. 记录完整的车辆行程
CREATE TABLE trips (
    trip_id INTEGER PRIMARY KEY, -- 行程唯一标识（主键）
    pickup_datetime TEXT, -- 上车时间
    dropoff_datetime TEXT, -- 下车时间
    pickup_edge TEXT, -- 上车位置（路网边ID）
    dropoff_edge TEXT, -- 下车位置（路网边ID）
    passenger_count INTEGER, -- 乘客数量
    trip_distance REAL, -- 行程总距离
    pickup_x REAL, -- 上车点横坐标
    pickup_y REAL, -- 上车点纵坐标
    dropoff_x REAL, -- 下车点横坐标
    dropoff_y REAL -- 下车点纵坐标
);

-- 2. 仿真出租车里面订单任务的执行状态
CREATE TABLE simulation_tasks (
    task_id INTEGER PRIMARY KEY, -- 任务唯一标识（主键）
    dispatch_time TEXT, -- 任务派发时间（对应trips表的上车时间）
    origin_edge TEXT, -- 任务起始位置（路网边ID）
    dest_edge TEXT, -- 任务目的位置（路网边ID）
    status TEXT DEFAULT 'CREATED' -- 任务状态
);