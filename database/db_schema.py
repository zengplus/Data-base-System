import os
import sqlite3
import config

def get_db_connection(db_path=config.DB_FILE):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path=config.DB_FILE, schema_path=config.SQL_FILE):
    """初始化数据库表结构"""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    with open(schema_path, 'r') as f:
        cursor.executescript(f.read())
    conn.commit()
    conn.close()
