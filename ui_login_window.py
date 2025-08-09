from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont

from data_manager import DataManager

class LoginWindow(QWidget):
    """Прозорец за вход на потребител."""
    login_successful = Signal(str)  # Сигнал, който се изпраща с ролята на потребителя

    def __init__(self):
        super().__init__()
        self.setWindowTitle("TSA-Security - Вход")
        self.setFixedSize(400, 300)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Заглавие
        title_label = QLabel("TSA-Security")
        font = QFont()
        font.setPointSize(24)
        font.setBold(True)
        title_label.setFont(font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Полета за въвеждане
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Потребителско име")
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Парола")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

        # Бутон за вход
        login_button = QPushButton("Вход")
        login_button.clicked.connect(self.check_credentials)
        # Позволява натискане на Enter за вход
        self.password_input.returnPressed.connect(self.check_credentials)

        # Съобщение за грешка
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #F44747;") # Червен цвят за грешки
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Добавяне на елементите към лейаута
        main_layout.addWidget(title_label)
        main_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
        main_layout.addWidget(self.username_input)
        main_layout.addWidget(self.password_input)
        main_layout.addWidget(self.error_label)
        main_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum))
        main_layout.addWidget(login_button)
        main_layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))

    def check_credentials(self):
        """Проверява въведените потребителско име и парола."""
        username = self.username_input.text()
        password = self.password_input.text()
        
        if not username or not password:
            self.error_label.setText("Моля, попълнете всички полета.")
            return

        users = DataManager.load_users()
        for user in users:
            if user["username"] == username and user["password"] == password:
                print("Успешен вход!")
                self.login_successful.emit(user["role"]) # Изпращаме сигнал
                self.close() # Затваряме прозореца за вход
                return
        
        self.error_label.setText("Грешно потребителско име или парола.")