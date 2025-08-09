import json
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

class DataManager:
    @staticmethod
    def load_users():
        DATA_DIR.mkdir(exist_ok=True)
        users_file = DATA_DIR / "users.json"
        if not users_file.exists():
            raise FileNotFoundError("Файлът 'users.json' липсва. Моля, създайте го.")
            
        with open(users_file, "r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def load_cameras():
        DATA_DIR.mkdir(exist_ok=True)
        cameras_file = DATA_DIR / "cameras.json"
        if not cameras_file.exists():
            return []

        try:
            with open(cameras_file, "r", encoding="utf-8") as f:
                content = f.read()
                if not content:
                    return []
                return json.loads(content)
        except json.JSONDecodeError:
            print("Предупреждение: Файлът 'cameras.json' е повреден или в грешен формат.")
            return []

    @staticmethod
    def save_cameras(cameras_data):
        DATA_DIR.mkdir(exist_ok=True)
        cameras_file = DATA_DIR / "cameras.json"
        with open(cameras_file, "w", encoding="utf-8") as f:
            json.dump(cameras_data, f, indent=4, ensure_ascii=False)

    @staticmethod
    def load_events():
        DATA_DIR.mkdir(exist_ok=True)
        events_file = DATA_DIR / "events.json"

        if not events_file.exists():
            return []

        try:
            with open(events_file, "r", encoding="utf-8") as f:
                content = f.read()
                if not content:
                    return []
                return json.loads(content)
        except json.JSONDecodeError:
            print("Предупреждение: Файлът 'events.json' е повреден или в грешен формат.")
            return []

    @staticmethod
    def save_events(events_data):
        """Записва списъка със събития в events.json."""
        DATA_DIR.mkdir(exist_ok=True)
        events_file = DATA_DIR / "events.json"
        with open(events_file, "w", encoding="utf-8") as f:
            json.dump(events_data, f, indent=4, ensure_ascii=False)