import requests
import json
import base64
import urllib.parse

class RemoteClient:
    def __init__(self, host, port=8989, username=None, password=None):
        self.base_url = f"http://{host}:{port}"
        self.auth_headers = {}
        if username and password:
            credentials = f"{username}:{password}"
            encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
            self.auth_headers['Authorization'] = f'Basic {encoded_credentials}'

    def _get_json(self, endpoint):
        """Изпраща GET заявка и очаква JSON отговор."""
        try:
            response = requests.get(f"{self.base_url}{endpoint}", headers=self.auth_headers, timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Грешка при GET заявка към {endpoint}: {e}")
            return None

    def _post_json(self, endpoint, data):
        """Изпраща POST заявка с JSON данни."""
        headers = self.auth_headers.copy()
        headers['Content-Type'] = 'application/json'
        try:
            response = requests.post(f"{self.base_url}{endpoint}", headers=headers, data=json.dumps(data), timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Грешка при POST заявка към {endpoint}: {e}")
            return None

    def get_cameras(self):
        """Взима списъка с камери от отдалечена инстанция."""
        return self._get_json('/api/cameras')

    def get_recordings(self):
        """Взима списъка със записи от отдалечена инстанция."""
        return self._get_json('/api/recordings')

    def download_file(self, remote_path, local_path, progress_callback=None, check_cancel_callback=None):
        """Изтегля файл от отдалечената система с опция за прогрес и прекратяване."""
        encoded_path = urllib.parse.quote(remote_path)
        try:
            with requests.get(f"{self.base_url}/api/download?path={encoded_path}", headers=self.auth_headers, stream=True, timeout=30) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))
                bytes_downloaded = 0
                with open(local_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if check_cancel_callback and check_cancel_callback():
                            print("Изтеглянето е прекратено от потребителя.")
                            return False, "Download canceled"
                        f.write(chunk)
                        bytes_downloaded += len(chunk)
                        if progress_callback and total_size > 0:
                            progress = int((bytes_downloaded / total_size) * 100)
                            progress_callback(progress)
            return True, str(local_path)
        except requests.exceptions.RequestException as e:
            error_message = f"Грешка при изтегляне на файла: {e}"
            print(error_message)
            return False, error_message
        except Exception as e:
            error_message = f"Грешка при запис на файла: {e}"
            print(error_message)
            return False, error_message

    def send_action(self, action, payload):
        """Изпраща команда към отдалечения сървър."""
        data = {"action": action, "payload": payload}
        return self._post_json('/api/action', data)

    def test_connection(self):
        """Тества дали връзката е успешна."""
        return self.get_cameras() is not None