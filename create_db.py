from config import DB_PATH
import sqlite3
import os

def ensure_sensors_table(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sensors'")
    if cursor.fetchone() is None:
        cursor.execute('''
            CREATE TABLE sensors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                ip_address TEXT,
                hostname TEXT,
                service TEXT,
                sensor_name TEXT,
                sensor_value REAL,
                sensor_unit TEXT,
                sensor_type TEXT,
                adapter TEXT,
                device TEXT
            )
        ''')
    else:
        cursor.execute("PRAGMA table_info(sensors)")
        columns = {row[1] for row in cursor.fetchall()}
        
        if 'sensor_type' not in columns:
            cursor.execute('ALTER TABLE sensors ADD COLUMN sensor_type TEXT')
        if 'adapter' not in columns:
            cursor.execute('ALTER TABLE sensors ADD COLUMN adapter TEXT')
        if 'device' not in columns:
            cursor.execute('ALTER TABLE sensors ADD COLUMN device TEXT')
    conn.commit()

def create_database():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    ensure_sensors_table(conn)
    conn.close()
    print("Database created/updated successfully")
    print("База данных успешно создана/обновлена")