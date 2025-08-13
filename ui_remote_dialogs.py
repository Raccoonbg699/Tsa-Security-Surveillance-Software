import uuid
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QDialogButtonBox,
    QFormLayout, QMessageBox, QApplication
)
from PySide6.QtCore import Qt, Signal
from data_manager import get_translator, DataManager
from remote_client import RemoteClient

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
        self.list_widget.clear()
        systems = DataManager.load_remote_systems()
        for system in systems:
            item = QListWidgetItem(f"{system['name']} ({system['ip']})")
            item.setData(Qt.ItemDataRole.UserRole, system)
            self.list_widget.addItem(item)

    def save_systems(self, systems_data):
        DataManager.save_remote_systems(systems_data)
        self.load_systems()
        
    def add_system(self):
        dialog = RemoteSystemDialog(parent=self)
        if dialog.exec():
            new_data = dialog.get_data()
            if not all(new_data.values()):
                QMessageBox.warning(self, "Грешка", "Всички полета са задължителни.")
                return
            new_data["id"] = str(uuid.uuid4())
            systems = DataManager.load_remote_systems()
            systems.append(new_data)
            self.save_systems(systems)

    def edit_system(self):
        selected_items = self.list_widget.selectedItems()
        if not selected_items: return
        system_to_edit = selected_items[0].data(Qt.ItemDataRole.UserRole)
        
        dialog = RemoteSystemDialog(system_data=system_to_edit, parent=self)
        if dialog.exec():
            updated_data = dialog.get_data()
            if not all(updated_data.values()):
                QMessageBox.warning(self, "Грешка", "Всички полета са задължителни.")
                return
            
            systems = DataManager.load_remote_systems()
            for i, system in enumerate(systems):
                if system.get("id") == system_to_edit.get("id"):
                    updated_data["id"] = system_to_edit.get("id")
                    systems[i] = updated_data
                    break
            self.save_systems(systems)

    def delete_system(self):
        selected_items = self.list_widget.selectedItems()
        if not selected_items: return
        system_to_delete = selected_items[0].data(Qt.ItemDataRole.UserRole)

        reply = QMessageBox.question(self, "Потвърждение", f"Изтриване на '{system_to_delete['name']}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            systems = DataManager.load_remote_systems()
            updated_systems = [s for s in systems if s.get("id") != system_to_delete.get("id")]
            self.save_systems(updated_systems)
        
    def connect_to_system(self):
        selected_items = self.list_widget.selectedItems()
        if not selected_items:
            return
        system_data = selected_items[0].data(Qt.ItemDataRole.UserRole)
        
        client = RemoteClient(host=system_data["ip"], username=system_data["username"], password=system_data["password"])
        
        self.connect_button.setEnabled(False)
        self.connect_button.setText("Свързване...")
        QApplication.processEvents()
        
        if client.test_connection():
            QMessageBox.information(self, "Успех", f"Успешна връзка със система '{system_data['name']}'!")
            self.connection_successful.emit(client)
            self.accept()
        else:
            QMessageBox.critical(self, "Грешка", f"Неуспешна връзка със система '{system_data['name']}'.\nПроверете IP адреса, потребителското име и паролата.")
            self.connect_button.setText("Свържи се")
            self.on_selection_changed()