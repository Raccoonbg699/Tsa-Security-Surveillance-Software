import os
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication

os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"

from ui_login_window import LoginWindow
from ui_main_window import MainWindow
from data_manager import DataManager, get_translator
# --- ПРОМЯНА: Импортираме нашия API сървър ---
from api_server import ApiServer

BASE_DIR = Path(__file__).parent

class ApplicationController:
    """Управлява потока на приложението."""
    def __init__(self, app):
        self.app = app
        self.login_window = None
        self.main_window = None
        # --- ПРОМЯНА: Създаваме инстанция на сървъра ---
        self.api_server = ApiServer()

    def start(self):
        """Показва прозореца за вход и стартира API сървъра."""
        # --- ПРОМЯНА: Стартираме сървъра ---
        self.api_server.start()

        translator = get_translator()
        settings = DataManager.load_settings()
        translator.set_language(settings.get("language", "bg"))

        self.login_window = LoginWindow()
        self.login_window.login_successful.connect(self.show_main_window)
        self.login_window.restart_requested.connect(self.restart)
        self.login_window.show()

    def show_main_window(self, user_role):
        """Показва главния прозорец след успешен вход."""
        print(f"Потребител с роля '{user_role}' влезе в системата.")
        self.main_window = MainWindow(base_dir=BASE_DIR, user_role=user_role)
        self.main_window.logout_requested.connect(self.handle_logout)
        self.main_window.restart_requested.connect(self.restart)
        self.main_window.show()

    def handle_logout(self):
        """Затваря главния прозорец и показва отново екрана за вход."""
        if self.main_window:
            self.main_window.close()
            self.main_window = None
        # Не спираме сървъра, за да може да се логне друг потребител
        self.start()
        
    def restart(self):
        """Затваря всички прозорци и стартира приложението отначало."""
        print("Рестартиране на приложението за смяна на език...")
        if self.login_window:
            self.login_window.close()
            self.login_window = None
        if self.main_window:
            self.main_window.close()
            self.main_window = None
        self.start()


def main():
    """Основна функция за стартиране на приложението."""
    app = QApplication(sys.argv)
    
    translator = get_translator()
    translator.load_translations()
    
    try:
        settings = DataManager.load_settings()
        theme = settings.get("theme", "dark")
        style_file_name = "style.qss" if theme == "dark" else "style_light.qss"
        style_file = BASE_DIR / style_file_name
        
        with open(style_file, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
            
    except FileNotFoundError:
        print(f"Предупреждение: Файл със стилове не е намерен.")

    controller = ApplicationController(app)
    controller.start()
    
    exit_code = app.exec()
    
    # --- ПРОМЯНА: Спираме сървъра при изход от приложението ---
    controller.api_server.stop()
    sys.exit(exit_code)

if __name__ == "__main__":
    main()