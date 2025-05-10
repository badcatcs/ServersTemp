from create_db import ensure_sensors_table, DB_PATH
from datetime import datetime
import socketserver
import threading
import sqlite3
import socket
import json
import re

class SyslogUDPServer(socketserver.UDPServer):
    def server_bind(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        socketserver.UDPServer.server_bind(self)
        print(f"UDP Server bound to {self.server_address}")

class SyslogTCPServer(socketserver.TCPServer):
    def server_bind(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        socketserver.TCPServer.server_bind(self)
        print(f"TCP Server bound to {self.server_address}")

class SyslogUDPHandler(socketserver.BaseRequestHandler):
    def parse_syslog_message(self, data):
        try:
            json_match = re.search(r'({.*})', data)
            if json_match:
                try:
                    data_json = json.loads(json_match.group(1))
                    if data_json.get('service') == 'sensors':
                        hostname = data_json.get('hostname', 'unknown')
                        service = data_json.get('service', 'unknown')
                        sensor_data = data_json
                        result = {
                            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'hostname': hostname,
                            'service': service,
                            'facility': '0',
                            'priority': '0',
                            'message': data,
                            'server_ip': self.client_address[0],
                            'sensor_data': sensor_data
                        }
                        return result
                except Exception as e:
                    print(f"Ошибка парсинга JSON в syslog (sensors): {e}")
            return {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'hostname': 'unknown',
                'service': 'unknown',
                'facility': '0',
                'priority': '0',
                'message': data,
                'server_ip': self.client_address[0],
                'sensor_data': None
            }
        except Exception as e:
            print(f"Error parsing syslog message: {e}")
            return None

    def save_to_db(self, log_data):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            if log_data['service'] == 'sensors' and log_data['sensor_data']:
                if isinstance(log_data['sensor_data'], str):
                    log_data['sensor_data'] = json.loads(log_data['sensor_data'])
                sensor_type = log_data['sensor_data'].get('sensor_type', 'unknown')
                adapter = log_data['sensor_data'].get('adapter', 'unknown')
                device = log_data['sensor_data'].get('device', 'unknown')
                ensure_sensors_table(conn)
                cursor.execute('''
                    INSERT INTO sensors (
                        timestamp, ip_address, hostname, service, 
                        sensor_name, sensor_value, sensor_unit,
                        sensor_type, adapter, device
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    log_data['timestamp'],
                    log_data['server_ip'],
                    log_data['hostname'],
                    log_data['service'],
                    log_data['sensor_data'].get('name'),
                    log_data['sensor_data'].get('value'),
                    log_data['sensor_data'].get('unit'),
                    sensor_type,
                    adapter,
                    device
                ))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error saving to database: {e}")

    def handle(self):
        try:
            data = bytes.decode(self.request[0].strip())
            print(f"Received UDP logs from {self.client_address[0]}:{self.client_address[1]}")
            log_data = self.parse_syslog_message(data)
            if log_data:
                self.save_to_db(log_data)
            else:
                print("Failed to parse log data")
        except Exception as e:
            print(f"Error in handle method: {e}")

class SyslogTCPHandler(socketserver.BaseRequestHandler):
    def handle(self):
        try:
            while True:
                data = self.request.recv(4096).strip()
                if not data:
                    break
                data = bytes.decode(data)
                print(f"Received TCP logs from {self.client_address[0]}:{self.client_address[1]}")
                log_data = self.parse_syslog_message(data)
                if log_data:
                    self.save_to_db(log_data)
                else:
                    print("Failed to parse log data")
        except Exception as e:
            print(f"Error in TCP handle method: {e}")
        finally:
            self.request.close()

    def parse_syslog_message(self, data):
        try:
            json_match = re.search(r'({.*})', data)
            if json_match:
                try:
                    data_json = json.loads(json_match.group(1))
                    if data_json.get('service') == 'sensors':
                        hostname = data_json.get('hostname', 'unknown')
                        service = data_json.get('service', 'unknown')
                        sensor_data = data_json
                        result = {
                            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'hostname': hostname,
                            'service': service,
                            'facility': '0',
                            'priority': '0',
                            'message': data,
                            'server_ip': self.client_address[0],
                            'sensor_data': sensor_data
                        }
                        return result
                except Exception as e:
                    print(f"Ошибка парсинга JSON в syslog (sensors): {e}")
            return {
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'hostname': 'unknown',
                'service': 'unknown',
                'facility': '0',
                'priority': '0',
                'message': data,
                'server_ip': self.client_address[0],
                'sensor_data': None
            }
        except Exception as e:
            print(f"Error parsing syslog message: {e}")
            return None

    def save_to_db(self, log_data):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            if log_data['service'] == 'sensors' and log_data['sensor_data']:
                if isinstance(log_data['sensor_data'], str):
                    log_data['sensor_data'] = json.loads(log_data['sensor_data'])
                sensor_type = log_data['sensor_data'].get('sensor_type', 'unknown')
                adapter = log_data['sensor_data'].get('adapter', 'unknown')
                device = log_data['sensor_data'].get('device', 'unknown')
                ensure_sensors_table(conn)
                cursor.execute('''
                    INSERT INTO sensors (
                        timestamp, ip_address, hostname, service, 
                        sensor_name, sensor_value, sensor_unit,
                        sensor_type, adapter, device
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    log_data['timestamp'],
                    log_data['server_ip'],
                    log_data['hostname'],
                    log_data['service'],
                    log_data['sensor_data'].get('name'),
                    log_data['sensor_data'].get('value'),
                    log_data['sensor_data'].get('unit'),
                    sensor_type,
                    adapter,
                    device
                ))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Error saving to database: {e}")

def start_syslog_server(host='0.0.0.0', port=5141):
    try:
        udp_server = SyslogUDPServer((host, port), SyslogUDPHandler)
        udp_thread = threading.Thread(target=udp_server.serve_forever)
        udp_thread.daemon = True
        udp_thread.start()
        print(f"Started UDP syslog server on {host}:{port}")

        tcp_server = SyslogTCPServer((host, port + 1), SyslogTCPHandler)
        tcp_thread = threading.Thread(target=tcp_server.serve_forever)
        tcp_thread.daemon = True
        tcp_thread.start()
        print(f"Started TCP syslog server on {host}:{port + 1}")

        return udp_server, tcp_server
    except Exception as e:
        print(f"Error starting syslog server: {e}")
        if isinstance(e, socket.error) and e.errno == 98:
            try:
                port += 2
                print(f"Trying ports {port} and {port + 1}...")
                udp_server = SyslogUDPServer((host, port), SyslogUDPHandler)
                tcp_server = SyslogTCPServer((host, port + 1), SyslogTCPHandler)
                udp_thread = threading.Thread(target=udp_server.serve_forever)
                tcp_thread = threading.Thread(target=tcp_server.serve_forever)
                udp_thread.daemon = True
                tcp_thread.daemon = True
                udp_thread.start()
                tcp_thread.start()
                print(f"Successfully started on ports {port} and {port + 1}")
                return udp_server, tcp_server
            except Exception as e2:
                print(f"Failed to start on alternative ports: {e2}")
        else:
            print("Failed to start syslog server")
        return None, None

if __name__ == "__main__":
    udp_server, tcp_server = start_syslog_server()
    if udp_server and tcp_server:
        print("Syslog servers started. Press Ctrl+C to stop.")
        try:
            while True:
                pass
        except KeyboardInterrupt:
            print("Stopping syslog servers...")
            udp_server.shutdown()
            tcp_server.shutdown()