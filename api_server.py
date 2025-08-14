import json
import base64
import os
import mimetypes
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
from data_manager import DataManager

def is_authenticated(auth_header):
    """Проверява Authorization хедъра за валидни потребителски данни."""
    if auth_header is None or not auth_header.startswith('Basic '):
        return False
    
    # Декодираме base64 данните
    encoded_credentials = auth_header.split(' ')[1]
    decoded_credentials = base64.b64decode(encoded_credentials).decode('utf-8')
    username, password = decoded_credentials.split(':', 1)
    
    # Проверяваме в нашия users.json файл
    users = DataManager.load_users()
    for user in users:
        if user["username"] == username and user["password"] == password:
            # Важно: За сигурност, позволяваме достъп само на администратори
            if user["role"] == "Administrator":
                return True
    
    return False

class ApiHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        auth_header = self.headers.get('Authorization')
        if not is_authenticated(auth_header):
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b"Unauthorized")
            return

        if self.path == '/api/cameras':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            cameras = DataManager.load_cameras()
            self.wfile.write(json.dumps(cameras).encode('utf-8'))
        
        elif self.path == '/api/recordings':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            events = DataManager.load_events()
            self.wfile.write(json.dumps(events).encode('utf-8'))
            
        elif self.path.startswith('/api/download'):
            query_components = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            file_path_encoded = query_components.get("path", [None])[0]
            if not file_path_encoded:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Bad Request: Missing path parameter")
                return
            
            file_path = urllib.parse.unquote(file_path_encoded)
            
            if os.path.exists(file_path) and os.path.isfile(file_path):
                try:
                    with open(file_path, 'rb') as f:
                        self.send_response(200)
                        self.send_header('Content-type', mimetypes.guess_type(file_path)[0] or 'application/octet-stream')
                        fs = os.fstat(f.fileno())
                        self.send_header("Content-Length", str(fs.st_size))
                        self.end_headers()
                        self.wfile.write(f.read())
                except Exception as e:
                    self.send_response(500)
                    self.end_headers()
                    self.wfile.write(f"Server Error: {e}".encode('utf-8'))
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"File Not Found")
            
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

class ApiServer:
    def __init__(self, host='0.0.0.0', port=8989):
        self.host = host
        self.port = port
        self.server = None
        self.thread = None

    def start(self):
        """Стартира сървъра в отделна нишка."""
        if self.thread is not None and self.thread.is_alive():
            print("Сървърът вече работи.")
            return

        self.server = HTTPServer((self.host, self.port), ApiHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        print(f"API сървърът стартира на {self.host}:{self.port}")

    def stop(self):
        """Спира сървъра."""
        if self.server:
            print("API сървърът се спира...")
            self.server.shutdown()
            self.server.server_close()
            self.thread.join()
            print("API сървърът е спрян.")