import requests
import json
import base64

class RemoteClient:
    def __init__(self, host, port=8989, username=None, password=None):
        self.base_url = f"http://{host}:{port}"
        self.headers = {'Content-Type': 'application/json'}
        if username and password:
            credentials = f"{username}:{password}"
            encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
            self.headers['Authorization'] = f'Basic {encoded_credentials}'

    def _request(self, method, endpoint, data=None):
        try:
            if method.upper() == 'GET':
                response = requests.get(f"{self.base_url}{endpoint}", headers=self.headers, timeout=5)
            elif method.upper() == 'POST':
                response = requests.post(f"{self.base_url}{endpoint}", headers=self.headers, data=json.dumps(data), timeout=10)
            else:
                return None
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Грешка при комуникация с отдалечената система: {e}")
            return None

    def get_cameras(self):
        """Взима списъка с камери от отдалечена инстанция."""
        return self._request('GET', '/api/cameras')

    def get_recordings(self):
        """Взима списъка със записи от отдалечена инстанция."""
        return self._request('GET', '/api/recordings')

    def send_action(self, action, payload):
        """Изпраща команда към отдалечения сървър."""
        data = {"action": action, "payload": payload}
        return self._request('POST', '/api/action', data)

    def test_connection(self):
        """Тества дали връзката е успешна."""
        return self.get_cameras() is not None