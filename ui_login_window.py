from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, 
    QPushButton, QSpacerItem, QSizePolicy, QHBoxLayout
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont, QPixmap

from data_manager import DataManager

class LoginWindow(QWidget):
    login_successful = Signal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("LoginPage")
        self.setWindowTitle("Tsa-Security - Вход")
        # --- ПРОМЯНА: Увеличаваме размера на прозореца ---
        self.setFixedSize(700, 500)
        
        main_layout = QVBoxLayout(self)
        # Намаляваме вертикалните отстояния, за да има повече място
        main_layout.setContentsMargins(70, 20, 70, 50)

        # КОНТЕЙНЕР ЗА ЗАГЛАВИЕ И ЛОГО
        title_container = QWidget()
        title_container.setMinimumHeight(140) # Осигуряваме достатъчно височина
        title_container.setStyleSheet("background-color: transparent;")

        title_layout = QHBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setAlignment(Qt.AlignmentFlag.AlignCenter) 
        
        logo_label = QLabel()
        pixmap = QPixmap("Tsa-Security_logo_original_500х500-removebg-preview.png")

        # Запазваме уголемения размер
        logo_label.setPixmap(pixmap.scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        
        title_label = QLabel("Добре Дошли")
        title_label.setObjectName("LoginTitle")
        
        title_layout.addWidget(logo_label)
        title_layout.addSpacerItem(QSpacerItem(10, 20, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum))
        title_layout.addWidget(title_label)

        # Полета за въвеждане
        user_label = QLabel("Потребителско име")
        user_label.setObjectName("LoginLabel")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Въведете потребителско име")
        
        pass_label = QLabel("Парола")
        pass_label.setObjectName("LoginLabel")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Въведете парола")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

        # Бутон за вход
        login_button = QPushButton("Вход")
        login_button.setObjectName("AccentButton")
        login_button.setFixedHeight(45)
        login_button.clicked.connect(self.check_credentials)
        self.password_input.returnPressed.connect(self.check_credentials)

        # Етикет за грешки
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #F44747;")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setFixedHeight(20)

        main_layout.addStretch()
        main_layout.addWidget(title_container)
        main_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum))
        main_layout.addWidget(user_label)
        main_layout.addWidget(self.username_input)
        main_layout.addSpacerItem(QSpacerItem(20, 15, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum))
        main_layout.addWidget(pass_label)
        main_layout.addWidget(self.password_input)
        main_layout.addWidget(self.error_label)
        main_layout.addStretch()
        main_layout.addWidget(login_button)
        
    def check_credentials(self):
        username = self.username_input.text()
        password = self.password_input.text()
        if not username or not password:
            self.error_label.setText("Моля, попълнете всички полета.")
            return

        users = DataManager.load_users()
        for user in users:
            if user["username"] == username and user["password"] == password:
                print("Успешен вход!")
                self.login_successful.emit(user["role"])
                self.close()
                return
        
        self.error_label.setText("Грешно потребителско име или парола.")