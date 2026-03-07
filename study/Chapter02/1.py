import os
import sys
import csv
import time
import sqlite3
import urllib.request
from pathlib import Path

try:
    import traci
    from sumolib import checkBinary
    SUMO_AVAILABLE = True
except Exception:
    SUMO_AVAILABLE = False
    traci = None

BASE = Path(__file__).parent
DB_PATH = BASE / "taxi_chapter02.db"
CSV_PATH = BASE / "data" / "taxi_sample.csv"
SQL_PATH = BASE / "init_db.sql"
SUMO_CFG = BASE / "cross.sumocfg"
DATA_URLS = [
    "https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2015-01.csv",
    "https://s3.amazonaws.com/nyc-tlc/trip+data/yellow_tripdata_2015-01.csv"
]
MAX_LINES = 1200

def fetch_csv(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, timeout=30) as r, open(CSV_PATH, "wb") as f:
        for i, line in enumerate(r):
            if i >= MAX_LINES:
                break
            f.write(line)

def generate_sample_csv():
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        ["tpep_pickup_datetime","tpep_dropoff_datetime","passenger_count","trip_distance","pickup_longitude","pickup_latitude","dropoff_longitude","dropoff_latitude"],
        ["2015-01-01 00:01:00","2015-01-01 00:10:00","1","1.2","-73.985","40.758","-73.975","40.752"],
        ["2015-01-01 00:05:00","2015-01-01 00:18:00","2","2.5","-73.990","40.746","-73.980","40.736"],
        ["2015-01-01 00:12:00","2015-01-01 00:22:00","1","1.8","-73.970","40.762","-73.960","40.751"],
        ["2015-01-01 00:20:00","2015-01-01 00:40:00","3","3.1","-73.995","40.728","-73.985","40.739"]
    ]
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

def download_data():
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    if CSV_PATH.exists():
        return
    for url in DATA_URLS:
        try:
            fetch_csv(url)
            if CSV_PATH.exists() and CSV_PATH.stat().st_size > 0:
                return
        except Exception:
            continue
    generate_sample_csv()

def init_db():
    if not SQL_PATH.exists():
        raise FileNotFoundError(str(SQL_PATH))
    with sqlite3.connect(DB_PATH) as conn:
        with open(SQL_PATH, "r", encoding="utf-8") as f:
            conn.executescript(f.read())

def load_db():
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        with open(CSV_PATH, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        trip_rows = []
        req_rows = []
        for r in rows:
            pickup_dt = r.get("tpep_pickup_datetime") or r.get("pickup_datetime") or ""
            dropoff_dt = r.get("tpep_dropoff_datetime") or r.get("dropoff_datetime") or ""
            p_lon = r.get("pickup_longitude") or r.get("Pickup_longitude") or r.get("startLon")
            p_lat = r.get("pickup_latitude") or r.get("Pickup_latitude") or r.get("startLat")
            d_lon = r.get("dropoff_longitude") or r.get("Dropoff_longitude") or r.get("endLon")
            d_lat = r.get("dropoff_latitude") or r.get("Dropoff_latitude") or r.get("endLat")
            try:
                trip_rows.append((
                    pickup_dt,
                    dropoff_dt,
                    int(r.get("passenger_count") or 1),
                    float(r.get("trip_distance") or 0),
                    float(p_lon) if p_lon else None,
                    float(p_lat) if p_lat else None,
                    float(d_lon) if d_lon else None,
                    float(d_lat) if d_lat else None
                ))
                req_rows.append((
                    pickup_dt,
                    float(p_lon) if p_lon else None,
                    float(p_lat) if p_lat else None,
                    float(d_lon) if d_lon else None,
                    float(d_lat) if d_lat else None
                ))
            except Exception:
                continue
        cur.executemany(
            "INSERT INTO trips (pickup_datetime, dropoff_datetime, passenger_count, trip_distance, pickup_longitude, pickup_latitude, dropoff_longitude, dropoff_latitude) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            trip_rows
        )
        cur.executemany(
            "INSERT INTO requests (pickup_datetime, pickup_longitude, pickup_latitude, dropoff_longitude, dropoff_latitude) VALUES (?, ?, ?, ?, ?)",
            req_rows
        )
        conn.commit()

def run_sumo():
    if not SUMO_AVAILABLE:
        print("SUMO 不可用")
        return
    if not SUMO_CFG.exists():
        print("缺少 cross.sumocfg")
        return
    os.chdir(BASE)
    sumo_binary = checkBinary("sumo-gui")
    traci.start([sumo_binary, "-c", str(SUMO_CFG), "--start"])
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT request_id FROM requests LIMIT 20")
        reqs = [r[0] for r in cur.fetchall()]
    edges = [e for e in traci.edge.getIDList() if not e.startswith(":")]
    if not edges:
        print("没有可用边")
        return
    base_edge = edges[0]
    for i, rid in enumerate(reqs):
        route_id = f"r_{rid}"
        veh_id = f"veh_{rid}"
        traci.route.add(route_id, [base_edge])
        if hasattr(traci.edge, "getLength"):
            edge_len = traci.edge.getLength(base_edge)
        else:
            lane_id = base_edge + "_0"
            edge_len = traci.lane.getLength(lane_id)
        depart_pos = min(5.0 + i * 5.0, max(1.0, edge_len - 1.0))
        traci.vehicle.add(veh_id, route_id, departPos=str(depart_pos))
        traci.vehicle.setColor(veh_id, (255, 200, 0, 255))
    while True:
        traci.simulationStep()
        time.sleep(0.1)

if __name__ == "__main__":
    download_data()
    init_db()
    load_db()
    run_sumo()
