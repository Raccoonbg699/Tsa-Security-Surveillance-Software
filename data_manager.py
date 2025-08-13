import json
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"

class Translator:
    def __init__(self):
        self.translations = {}
        self.language = "bg"

    def load_translations(self):
        translations_file = DATA_DIR / "translations.json"
        try:
            with open(translations_file, "r", encoding="utf-8") as f:
                self.translations = json.load(f)
        except FileNotFoundError:
            print(f"ГРЕШКА: Файлът с преводи {translations_file} не е намерен!")
            self.translations = {}

    def set_language(self, language):
        if language in self.translations:
            self.language = language
        else:
            print(f"Предупреждение: Език '{language}' не е намерен. Използва се '{self.language}'.")

    def get_string(self, key):
        return self.translations.get(self.language, {}).get(key, key)

_translator_instance = None
def get_translator():
    global _translator_instance
    if _translator_instance is None:
        _translator_instance = Translator()
    return _translator_instance

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
    def save_users(users_data):
        DATA_DIR.mkdir(exist_ok=True)
        users_file = DATA_DIR / "users.json"
        with open(users_file, "w", encoding="utf-8") as f:
            json.dump(users_data, f, indent=4, ensure_ascii=False)

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
        DATA_DIR.mkdir(exist_ok=True)
        events_file = DATA_DIR / "events.json"
        with open(events_file, "w", encoding="utf-8") as f:
            json.dump(events_data, f, indent=4, ensure_ascii=False)
            
    @staticmethod
    def load_settings():
        DATA_DIR.mkdir(exist_ok=True)
        settings_file = DATA_DIR / "settings.json"
        defaults = {
            "theme": "dark",
            "default_grid": "2x2",
            "recording_path": str(Path.home() / "Videos" / "TSA-Security"),
            "language": "bg",
            "recording_structure": "single"
        }
        if not settings_file.exists():
            return defaults
        try:
            with open(settings_file, "r", encoding="utf-8") as f:
                settings = json.load(f)
                for key, value in defaults.items():
                    if key not in settings:
                        settings[key] = value
                return settings
        except json.JSONDecodeError:
            print("Предупреждение: Файлът 'settings.json' е повреден. Зареждат се настройки по подразбиране.")
            return defaults

    @staticmethod
    def save_settings(settings_data):
        DATA_DIR.mkdir(exist_ok=True)
        settings_file = DATA_DIR / "settings.json"
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(settings_data, f, indent=4, ensure_ascii=False)

    @staticmethod
    def load_remote_systems():
        DATA_DIR.mkdir(exist_ok=True)
        systems_file = DATA_DIR / "remote_systems.json"
        if not systems_file.exists():
            return []
        try:
            with open(systems_file, "r", encoding="utf-8") as f:
                content = f.read()
                if not content: return []
                return json.loads(content)
        except json.JSONDecodeError:
            print("Предупреждение: Файлът 'remote_systems.json' е повреден.")
            return []

    @staticmethod
    def save_remote_systems(systems_data):
        DATA_DIR.mkdir(exist_ok=True)
        systems_file = DATA_DIR / "remote_systems.json"
        with open(systems_file, "w", encoding="utf-8") as f:
            json.dump(systems_data, f, indent=4, ensure_ascii=False)