from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QLineEdit, 
    QPushButton, QSpacerItem, QSizePolicy, QHBoxLayout, QMenu, QToolButton
)
from PySide6.QtCore import Signal, Qt, QSize
from PySide6.QtGui import QFont, QPixmap, QAction

# --- ПРОМЯНА: Импортираме функцията get_translator ---
from data_manager import DataManager, get_translator

class LoginWindow(QWidget):
    login_successful = Signal(str)
    # --- ПРОМЯНА: Нов сигнал за рестарт с нов език ---
    restart_requested = Signal()

    def __init__(self):
        super().__init__()
        # --- ПРОМЯНА: Взимаме инстанцията на преводача ---
        self.translator = get_translator()
        self.setObjectName("LoginPage")
        
        # --- ПРОМЯНА: Всички текстове вече идват от преводача ---
        self.setWindowTitle(self.translator.get_string("login_window_title"))
        self.setFixedSize(700, 500)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(70, 20, 70, 50)

        # --- НОВА ЛОГИКА ЗА БУТОН ЗА ЕЗИК ---
        lang_button_layout = QHBoxLayout()
        lang_button_layout.addStretch()
        
        self.lang_button = QToolButton()
        self.lang_button.setText("🌐") # Икона на планета
        self.lang_button.setObjectName("LangButton")
        self.lang_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)

        lang_menu = QMenu(self)
        bg_action = QAction("Български", self)
        en_action = QAction("English", self)
        
        bg_action.triggered.connect(lambda: self.change_language("bg"))
        en_action.triggered.connect(lambda: self.change_language("en"))

        lang_menu.addAction(bg_action)
        lang_menu.addAction(en_action)
        self.lang_button.setMenu(lang_menu)
        lang_button_layout.addWidget(self.lang_button)
        # --- Край на новата логика ---

        title_container = QWidget()
        title_container.setMinimumHeight(140)
        title_container.setStyleSheet("background-color: transparent;")

        title_layout = QHBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        logo_label = QLabel()
        pixmap = QPixmap("Tsa-Security_logo_original_500х500-removebg-preview.png")
        logo_label.setPixmap(pixmap.scaled(120, 120, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        
        self.title_label = QLabel(self.translator.get_string("login_title"))
        self.title_label.setObjectName("LoginTitle")
        
        title_layout.addWidget(logo_label)
        title_layout.addSpacerItem(QSpacerItem(10, 20, QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Minimum))
        title_layout.addWidget(self.title_label)

        self.user_label = QLabel(self.translator.get_string("username"))
        self.user_label.setObjectName("LoginLabel")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText(self.translator.get_string("username_placeholder"))
        
        self.pass_label = QLabel(self.translator.get_string("password"))
        self.pass_label.setObjectName("LoginLabel")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText(self.translator.get_string("password_placeholder"))
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

        self.login_button = QPushButton(self.translator.get_string("login_button"))
        self.login_button.setObjectName("AccentButton")
        self.login_button.setFixedHeight(45)
        self.login_button.clicked.connect(self.check_credentials)
        self.password_input.returnPressed.connect(self.check_credentials)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #F44747;")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setFixedHeight(20)
        
        main_layout.addLayout(lang_button_layout)
        main_layout.addWidget(title_container)
        main_layout.addWidget(self.user_label)
        main_layout.addWidget(self.username_input)
        main_layout.addSpacerItem(QSpacerItem(20, 15, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum))
        main_layout.addWidget(self.pass_label)
        main_layout.addWidget(self.password_input)
        main_layout.addWidget(self.error_label)
        main_layout.addStretch()
        main_layout.addWidget(self.login_button)
        
    def check_credentials(self):
        username = self.username_input.text()
        password = self.password_input.text()
        if not username or not password:
            self.error_label.setText(self.translator.get_string("error_fill_fields"))
            return

        users = DataManager.load_users()
        for user in users:
            if user["username"] == username and user["password"] == password:
                print("Успешен вход!")
                self.login_successful.emit(user["role"])
                self.close()
                return
        
        self.error_label.setText(self.translator.get_string("error_wrong_credentials"))

    def change_language(self, lang_code):
        """Запазва новия език и подава сигнал за рестарт на приложението."""
        settings = DataManager.load_settings()
        settings["language"] = lang_code
        DataManager.save_settings(settings)
        self.restart_requested.emit()