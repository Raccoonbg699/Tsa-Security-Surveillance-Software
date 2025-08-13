import uuid
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QDialogButtonBox,
    QFormLayout, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from data_manager import get_translator # Уверете се, че data_manager е достъпен
from remote_client import RemoteClient # Уверете се, че remote_client е достъпен

class RemoteSystemDialog(QDialog):
    """Диалогов прозорец за добавяне/редактиране на отдалечена система."""
    def __init__(self, system_data=None, parent=None):
        super().__init__(parent)
        self.translator = get_translator()
        self.is_edit_mode = system_data is not None
        
        window_title = "Редактиране на система" if self.is_edit_mode else "Добавяне на система"
        self.setWindowTitle(window_title)
        self.setMinimumWidth(400)

        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.name_input = QLineEdit()
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("100.x.x.x")
        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)

        if self.is_edit_mode:
            self.name_input.setText(system_data.get("name", ""))
            self.ip_input.setText(system_data.get("ip", ""))
            self.username_input.setText(system_data.get("username", ""))
            self.password_input.setText(system_data.get("password", ""))

        form_layout.addRow("Име на връзката:", self.name_input)
        form_layout.addRow("Tailscale IP адрес:", self.ip_input)
        form_layout.addRow("Потребителско име:", self.username_input)
        form_layout.addRow("Парола:", self.password_input)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        main_layout.addLayout(form_layout)
        main_layout.addWidget(self.button_box)

    def get_data(self):
        return {
            "name": self.name_input.text().strip(),
            "ip": self.ip_input.text().strip(),
            "username": self.username_input.text().strip(),
            "password": self.password_input.text()
        }

class RemoteSystemsPage(QDialog):
    """Прозорец за управление на отдалечени системи."""
    connection_successful = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.translator = get_translator()
        self.setWindowTitle("Отдалечени системи")
        self.setMinimumSize(600, 400)

        main_layout = QVBoxLayout(self)
        
        self.list_widget = QListWidget()
        self.list_widget.itemSelectionChanged.connect(self.on_selection_changed)
        self.list_widget.itemDoubleClicked.connect(self.connect_to_system)

        buttons_layout = QHBoxLayout()
        self.connect_button = QPushButton("Свържи се")
        self.add_button = QPushButton("Добави...")
        self.edit_button = QPushButton("Редактирай...")
        self.delete_button = QPushButton("Изтрий")
        
        self.connect_button.setObjectName("AccentButton")
        self.connect_button.setEnabled(False)
        self.edit_button.setEnabled(False)
        self.delete_button.setEnabled(False)

        buttons_layout.addStretch()
        buttons_layout.addWidget(self.add_button)
        buttons_layout.addWidget(self.edit_button)
        buttons_layout.addWidget(self.delete_button)
        buttons_layout.addWidget(self.connect_button)

        main_layout.addWidget(QLabel("Изберете система, към която да се свържете:"))
        main_layout.addWidget(self.list_widget)
        main_layout.addLayout(buttons_layout)
        
        self.add_button.clicked.connect(self.add_system)
        self.edit_button.clicked.connect(self.edit_system)
        self.delete_button.clicked.connect(self.delete_system)
        self.connect_button.clicked.connect(self.connect_to_system)
        
        self.load_systems()

    def on_selection_changed(self):
        is_selected = bool(self.list_widget.selectedItems())
        self.connect_button.setEnabled(is_selected)
        self.edit_button.setEnabled(is_selected)
        self.delete_button.setEnabled(is_selected)
        
    def load_systems(self):
        # Логика за зареждане от файл ще бъде добавена тук
        pass

    def save_systems(self):
        # Логика за запис във файл ще бъде добавена тук
        pass
        
    def add_system(self):
        # Логика за добавяне ще бъде добавена тук
        pass

    def edit_system(self):
        # Логика за редактиране ще бъде добавена тук
        pass

    def delete_system(self):
        # Логика за изтриване ще бъде добавена тук
        pass
        
    def connect_to_system(self):
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            return
        system_data = selected_items[0].data(Qt.ItemDataRole.UserRole)
        
        client = RemoteClient(host=system_data["ip"], username=system_data["username"], password=system_data["password"])
        
        if client.test_connection():
            QMessageBox.information(self, "Успех", f"Успешна връзка със система '{system_data['name']}'!")
            self.connection_successful.emit(system_data)
            self.accept()
        else:
            QMessageBox.critical(self, "Грешка", f"Неуспешна връзка със система '{system_data['name']}'.\nПроверете IP адреса, потребителското име и паролата.")