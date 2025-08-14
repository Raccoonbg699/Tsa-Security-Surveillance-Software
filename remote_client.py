import requests
import json
import base64
import urllib.parse

class RemoteClient:
    def __init__(self, host, port=8989, username=None, password=None):
        self.base_url = f"http://{host}:{port}"
        self.headers = {}
        if username and password:
            # Създаваме Basic Auth хедър
            credentials = f"{username}:{password}"
            encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
            self.headers['Authorization'] = f'Basic {encoded_credentials}'

    def _get(self, endpoint, stream=False):
        """Изпраща GET заявка към отдалечения сървър."""
        try:
            response = requests.get(f"{self.base_url}{endpoint}", headers=self.headers, timeout=5, stream=stream)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            print(f"Грешка при свързване с отдалечената система: {e}")
            return None

    def get_cameras(self):
        """Взима списъка с камери от отдалечена инстанция."""
        response = self._get('/api/cameras')
        return response.json() if response else None

    def get_recordings(self):
        """Взима списъка със записи от отдалечена инстанция."""
        response = self._get('/api/recordings')
        return response.json() if response else None

    def download_file(self, remote_path, local_path):
        """Изтегля файл от отдалечената система."""
        encoded_path = urllib.parse.quote(remote_path)
        response = self._get(f'/api/download?path={encoded_path}', stream=True)
        if response and response.status_code == 200:
            try:
                with open(local_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                return True
            except Exception as e:
                print(f"Грешка при запис на файла: {e}")
                return False
        return False

    def test_connection(self):
        """Тества дали връзката е успешна."""
        return self._get('/api/cameras') is not None