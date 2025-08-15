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
    
    encoded_credentials = auth_header.split(' ')[1]
    decoded_credentials = base64.b64decode(encoded_credentials).decode('utf-8')
    username, password = decoded_credentials.split(':', 1)
    
    users = DataManager.load_users()
    for user in users:
        if user["username"] == username and user["password"] == password:
            if user["role"] == "Administrator":
                return True
    
    return False

class ApiHandler(BaseHTTPRequestHandler):
    def __init__(self, command_queue, *args, **kwargs):
        self.command_queue = command_queue
        super().__init__(*args, **kwargs)

    def _send_response(self, code, content, content_type='application/json'):
        self.send_response(code)
        self.send_header('Content-type', content_type)
        self.end_headers()
        self.wfile.write(content.encode('utf-8'))

    def do_GET(self):
        auth_header = self.headers.get('Authorization')
        if not is_authenticated(auth_header):
            self._send_response(401, "Unauthorized", 'text/plain')
            return

        if self.path == '/api/cameras':
            cameras = DataManager.load_cameras()
            self._send_response(200, json.dumps(cameras))
        
        elif self.path == '/api/recordings':
            events = DataManager.load_events()
            self._send_response(200, json.dumps(events))
            
        else:
            self._send_response(404, "Not Found", 'text/plain')

    def do_POST(self):
        auth_header = self.headers.get('Authorization')
        if not is_authenticated(auth_header):
            self._send_response(401, "Unauthorized", 'text/plain')
            return

        if self.path == '/api/action':
            content_len = int(self.headers.get('Content-Length'))
            post_body = self.rfile.read(content_len)
            data = json.loads(post_body)
            
            # Поставяме командата в опашката за обработка от главната нишка
            self.command_queue.put(data)
            
            self._send_response(200, json.dumps({"status": "ok", "message": "Command queued."}))
        else:
            self._send_response(404, "Not Found", 'text/plain')


class ApiServer:
    def __init__(self, command_queue, host='0.0.0.0', port=8989):
        self.command_queue = command_queue
        self.host = host
        self.port = port
        self.server = None
        self.thread = None

    def start(self):
        """Стартира сървъра в отделна нишка."""
        if self.thread is not None and self.thread.is_alive():
            print("Сървърът вече работи.")
            return

        handler = lambda *args, **kwargs: ApiHandler(self.command_queue, *args, **kwargs)
        self.server = HTTPServer((self.host, self.port), handler)
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