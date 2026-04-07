-- 1. 车辆状态表
CREATE TABLE IF NOT EXISTS taxis (
    taxi_id TEXT PRIMARY KEY,
    status TEXT DEFAULT 'IDLE', -- IDLE, PICKUP, OCCUPIED, REBALANCING
    current_x REAL,
    current_y REAL,
    last_update INTEGER,
    cell_id TEXT -- V0.2: 新增网格ID索引
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
    status TEXT DEFAULT 'PENDING', -- PENDING, ASSIGNED, OCCUPIED, COMPLETED
    cell_id TEXT -- V0.2: 新增网格ID索引
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

-- 5. 重平衡日志表 (V0.2 新增)
CREATE TABLE IF NOT EXISTS rebalance_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    step INTEGER,
    taxi_id TEXT,
    from_cell TEXT,
    to_cell TEXT,
    dispatch_time INTEGER
);

-- 6. 路网状态快照表 (V0.2 新增)
CREATE TABLE IF NOT EXISTS traffic_state (
    step INTEGER,
    edge_id TEXT,
    speed REAL,
    congestion_level INTEGER,
    PRIMARY KEY(step, edge_id)
);
