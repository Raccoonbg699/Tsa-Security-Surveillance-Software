import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication

from ui_login_window import LoginWindow
from ui_main_window import MainWindow

# Определяме основната директория на проекта
BASE_DIR = Path(__file__).parent

class ApplicationController:
    """Управлява потока на приложението (кой прозорец кога да се покаже)."""
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
        # Подаваме основната директория към главния прозорец
        self.main_window = MainWindow(base_dir=BASE_DIR)
        self.main_window.show()


def main():
    """Основна функция за стартиране на приложението."""
    app = QApplication(sys.argv)
    
    # Зареждане на стиловете от QSS файла, използвайки пълния път
    style_file = BASE_DIR / "style.qss"
    try:
        with open(style_file, "r") as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        print(f"Предупреждение: Файлът {style_file} не е намерен. Ще се използва стандартен стил.")

    # Стартиране на приложението
    controller = ApplicationController(app)
    controller.start()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()