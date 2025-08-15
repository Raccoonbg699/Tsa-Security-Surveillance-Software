import requests
import json
import base64
import urllib.parse

class RemoteClient:
    def __init__(self, host, port=8989, username=None, password=None):
        self.base_url = f"http://{host}:{port}"
        self.headers = {'Content-Type': 'application/json'}
        if username and password:
            credentials = f"{username}:{password}"
            encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
            self.headers['Authorization'] = f'Basic {encoded_credentials}'

    def _request(self, method, endpoint, data=None, stream=False):
        """Универсален метод за заявки към сървъра."""
        try:
            url = f"{self.base_url}{endpoint}"
            if method.upper() == 'GET':
                response = requests.get(url, headers=self.headers, timeout=5, stream=stream)
            elif method.upper() == 'POST':
                headers = self.headers.copy()
                if data is None:
                    headers.pop('Content-Type', None)
                response = requests.post(url, headers=headers, data=json.dumps(data) if data else None, timeout=10)
            else:
                return None
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            print(f"Грешка при комуникация с отдалечената система: {e}")
            return None

    def get_cameras(self):
        """Взима списъка с камери от отдалечена инстанция."""
        response = self._request('GET', '/api/cameras')
        return response.json() if response else None

    def get_recordings(self):
        """Взима списъка със записи от отдалечена инстанция."""
        response = self._request('GET', '/api/recordings')
        return response.json() if response else None

    def download_file(self, remote_path, local_path):
        """Изтегля файл от отдалечената система."""
        encoded_path = urllib.parse.quote(remote_path)
        response = self._request('GET', f'/api/download?path={encoded_path}', stream=True)
        
        if response and response.status_code == 200:
            try:
                with open(local_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                return True
            except Exception as e:
                print(f"Грешка при запис на файла: {e}")
                return False
        print(f"Download failed with status code: {response.status_code if response else 'No response'}")
        return False

    def send_action(self, action, payload):
        """Изпраща команда към отдалечения сървър."""
        data = {"action": action, "payload": payload}
        response = self._request('POST', '/api/action', data)
        return response.json() if response else None

    def test_connection(self):
        """Тества дали връзката е успешна."""
        response = self._request('GET', '/api/cameras')
        return response is not None