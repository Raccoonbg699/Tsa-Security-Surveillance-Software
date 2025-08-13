import requests
import json

class RemoteClient:
    def __init__(self, host, port=8989, username=None, password=None):
        self.base_url = f"http://{host}:{port}"
        self.auth = (username, password) if username and password else None
        self.headers = {'Authorization': 'some_token'} # Ще го подобрим по-късно

    def _get(self, endpoint):
        """Изпраща GET заявка към отдалечения сървър."""
        try:
            response = requests.get(f"{self.base_url}{endpoint}", headers=self.headers, timeout=5)
            response.raise_for_status() # Хвърля грешка при неуспешни заявки (4xx или 5xx)
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Грешка при свързване с отдалечената система: {e}")
            return None # Връщаме None при грешка

    def get_cameras(self):
        """Взима списъка с камери от отдалечена инстанция."""
        return self._get('/api/cameras')

    def get_recordings(self):
        """Взима списъка със записи от отдалечена инстанция."""
        return self._get('/api/recordings')

    def test_connection(self):
        """Тества дали връзката е успешна."""
        # Правим заявка към защитен, но празен ендпойнт, само за да проверим автентикацията
        return self._get('/api/cameras') is not None