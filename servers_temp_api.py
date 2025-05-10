from flask import Flask, render_template, request, jsonify
from config import DB_PATH, DELETE_IN_DAYS
from datetime import datetime, timedelta
from collections import defaultdict
import threading
import sqlite3

app = Flask(__name__)

def get_all_sensors_latest():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT timestamp, hostname, sensor_name, sensor_value, sensor_unit, sensor_type, adapter, device 
            FROM sensors 
            ORDER BY timestamp DESC LIMIT 500
        ''')
        rows = cursor.fetchall()
        conn.close()
        servers = {}

        for row in rows:
            ts, hostname, name, value, unit, sensor_type, adapter, device = row
            if not hostname or not name or value is None:
                continue

            phys_server = hostname if hostname.startswith('server_') else 'unknown'
            if phys_server not in servers:
                servers[phys_server] = {
                    'timestamp': ts,
                    'sensors': {},
                    'sensor_types': set(),
                    'adapters': set()
                }

            if name not in servers[phys_server]['sensors']:
                servers[phys_server]['sensors'][name] = {
                    'value': float(value),
                    'unit': unit,
                    'type': sensor_type,
                    'adapter': adapter,
                    'device': device
                }
                servers[phys_server]['sensor_types'].add(sensor_type)
                servers[phys_server]['adapters'].add(adapter)
                if ts > servers[phys_server]['timestamp']:
                    servers[phys_server]['timestamp'] = ts

        for server, data in servers.items():
            for name, sensor in data['sensors'].items():
                lname = name.lower()
                sensor['is_temp'] = lname.startswith('temp')
                sensor['is_composite'] = lname == 'composite'

        return servers
    except Exception as e:
        print(f"Error in get_all_sensors_latest: {e}")
        return {}

@app.route('/')
def index():
    selected_server = request.args.get('phys_server', '')
    sensors_latest = get_all_sensors_latest()
    servers = list(sensors_latest.keys())
    if selected_server and selected_server in sensors_latest:
        sensors_latest = {selected_server: sensors_latest[selected_server]}
    return render_template('index.html', tab='sensors', sensors_latest=sensors_latest, servers=servers, selected_server=selected_server)

@app.route('/sensors_graphic')
def api_package_temps_week():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    seven_days_ago = (datetime.now() - timedelta(days=DELETE_IN_DAYS)).strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("DELETE FROM sensors WHERE timestamp < ?", (seven_days_ago,))
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'server_%'")
    server_tables = [row[0] for row in cursor.fetchall()]
    for table in server_tables:
        try:
            cursor.execute(f"DELETE FROM '{table}' WHERE timestamp < ?", (seven_days_ago,))
        except Exception as e:
            print(f"Error while deleting from {table}: {e}")
    conn.commit()

    week_ago = (datetime.now() - timedelta(days=DELETE_IN_DAYS)).strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("""
        SELECT timestamp, hostname, sensor_value
        FROM sensors
        WHERE sensor_name = 'Package id 0' AND timestamp >= ?
        ORDER BY timestamp ASC
    """, (week_ago,))
    rows = cursor.fetchall()
    conn.close()

    time_points = []
    servers = defaultdict(lambda: defaultdict(list))
    last_seen = {}

    for ts, host, val in rows:
        t = datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')
        tkey = t.strftime('%Y-%m-%d %H:00')
        time_points.append(tkey)
        servers[host][tkey].append(float(val))
        if host not in last_seen or ts > last_seen[host]:
            last_seen[host] = ts

    time_points = sorted(list(set(time_points)))
    data = {}
    for host in servers:
        data[host] = []
        for t in time_points:
            vals = servers[host].get(t, [])
            data[host].append(round(sum(vals)/len(vals), 1) if vals else None)

    statuses = {}
    now = datetime.now()
    for host, ts in last_seen.items():
        try:
            dt = datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')
            statuses[host] = (now - dt).total_seconds() < 60
        except Exception:
            statuses[host] = False

    return jsonify({
        "labels": time_points,
        "servers": data,
        "statuses": statuses
    })

if __name__ == '__main__':
    from syslog_server import start_syslog_server
    from create_db import create_database
    create_database()
    import threading

    syslog_thread = threading.Thread(target=start_syslog_server)
    syslog_thread.daemon = True
    syslog_thread.start()

    app.run(host='0.0.0.0', port=80, debug=True)
