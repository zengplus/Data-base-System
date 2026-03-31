-- 1. 车辆状态表
CREATE TABLE IF NOT EXISTS taxis (
    taxi_id TEXT PRIMARY KEY,
    status TEXT DEFAULT 'IDLE', -- IDLE, PICKUP, OCCUPIED
    current_x REAL,
    current_y REAL,
    last_update INTEGER
);

-- 2. 乘客请求表
CREATE TABLE IF NOT EXISTS trip_requests (
    request_id INTEGER PRIMARY KEY AUTOINCREMENT,
    dispatch_time INTEGER,
    origin_edge TEXT,
    dest_edge TEXT,
    origin_x REAL,
    origin_y REAL,
    dest_x REAL,
    dest_y REAL,
    status TEXT DEFAULT 'PENDING' -- PENDING, ASSIGNED, OCCUPIED, COMPLETED
);

-- 3. 分配记录表
CREATE TABLE IF NOT EXISTS assignments (
    assignment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id INTEGER,
    taxi_id TEXT,
    assign_time INTEGER,
    pickup_time INTEGER,
    dropoff_time INTEGER,
    wait_time INTEGER,
    FOREIGN KEY(request_id) REFERENCES trip_requests(request_id),
    FOREIGN KEY(taxi_id) REFERENCES taxis(taxi_id)
);

-- 4. R-Tree 虚拟表 (用于快速 KNN / 空间查询)
CREATE VIRTUAL TABLE IF NOT EXISTS taxi_locations USING rtree(
    id INTEGER,           -- 对应 taxis.taxi_id 的数字部分
    minX REAL, maxX REAL,
    minY REAL, maxY REAL
);
