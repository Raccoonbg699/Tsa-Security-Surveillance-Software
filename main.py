import os
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication

os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"

from ui_login_window import LoginWindow
from ui_main_window import MainWindow
from data_manager import DataManager

BASE_DIR = Path(__file__).parent

class ApplicationController:
    """Управлява потока на приложението."""
    def __init__(self, app):
        self.app = app
        self.login_window = None
        self.main_window = None

    def start(self):
        """Показва прозореца за вход."""
        self.login_window = LoginWindow()
        self.login_window.login_successful.connect(self.show_main_window)
        self.login_window.show()

    def show_main_window(self, user_role):
        """Показва главния прозорец след успешен вход."""
        print(f"Потребител с роля '{user_role}' влезе в системата.")
        self.main_window = MainWindow(base_dir=BASE_DIR, user_role=user_role)
        self.main_window.logout_requested.connect(self.handle_logout)
        self.main_window.show()

    def handle_logout(self):
        """Затваря главния прозорец и показва отново екрана за вход."""
        if self.main_window:
            self.main_window.close()
            self.main_window = None
        
        self.start()

def main():
    """Основна функция за стартиране на приложението."""
    app = QApplication(sys.argv)
    
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
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()