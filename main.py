import os
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication

# --- ТУК Е КЛЮЧОВАТА ПРОМЯНА ---
# Този ред трябва да е НАЙ-ОТГОРЕ, преди да се зареди каквото и да е друго.
# Той "казва" на OpenCV да предпочита TCP за RTSP. Това прави връзката много по-стабилна.
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"

from ui_login_window import LoginWindow
from ui_main_window import MainWindow

# Определяме основната директория на проекта
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
        self.main_window = MainWindow(base_dir=BASE_DIR)
        self.main_window.show()


def main():
    """Основна функция за стартиране на приложението."""
    app = QApplication(sys.argv)
    
    style_file = BASE_DIR / "style.qss"
    try:
        with open(style_file, "r") as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        print(f"Предупреждение: Файлът {style_file} не е намерен.")

    controller = ApplicationController(app)
    controller.start()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()