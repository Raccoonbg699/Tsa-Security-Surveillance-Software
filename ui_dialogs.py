from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QVBoxLayout, QFormLayout, 
    QLineEdit, QCheckBox, QLabel, QComboBox
)

class CameraDialog(QDialog):
    def __init__(self, camera_data=None, parent=None):
        super().__init__(parent)
        self.is_edit_mode = camera_data is not None
        
        window_title = "Редактиране на камера" if self.is_edit_mode else "Добавяне на нова камера"
        self.setWindowTitle(window_title)
        self.setMinimumWidth(400)

        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.name_input = QLineEdit()
        self.url_input = QLineEdit()
        self.status_checkbox = QCheckBox("Активна")
        # --- ПРОМЯНА: Добавяме отметка за детекция на движение ---
        self.motion_checkbox = QCheckBox("Детекция на движение")

        if self.is_edit_mode:
            self.name_input.setText(camera_data.get("name", ""))
            self.url_input.setText(camera_data.get("rtsp_url", ""))
            self.status_checkbox.setChecked(camera_data.get("is_active", True))
            # --- ПРОМЯНА: Задаваме състоянието на отметката ---
            self.motion_checkbox.setChecked(camera_data.get("motion_enabled", True))
        else:
            self.status_checkbox.setChecked(True)
            # Включена по подразбиране за нови камери
            self.motion_checkbox.setChecked(True)

        form_layout.addRow("Име на камера:", self.name_input)
        form_layout.addRow("RTSP Адрес:", self.url_input)
        form_layout.addRow(self.status_checkbox)
        # --- ПРОМЯНА: Добавяме я във формата ---
        form_layout.addRow(self.motion_checkbox) 

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        main_layout.addLayout(form_layout)
        main_layout.addWidget(self.button_box)

    def get_data(self):
        return {
            "name": self.name_input.text().strip(),
            "rtsp_url": self.url_input.text().strip(),
            "is_active": self.status_checkbox.isChecked(),
            # --- ПРОМЯНА: Връщаме новата стойност ---
            "motion_enabled": self.motion_checkbox.isChecked()
        }

class UserDialog(QDialog):
    """Диалогов прозорец за добавяне или редактиране на потребител."""
    def __init__(self, user_data=None, parent=None):
        super().__init__(parent)
        self.is_edit_mode = user_data is not None
        
        window_title = "Редактиране на потребител" if self.is_edit_mode else "Добавяне на нов потребител"
        self.setWindowTitle(window_title)
        self.setMinimumWidth(400)

        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.role_combo = QComboBox()
        self.role_combo.addItems(["Standard", "Administrator"])

        if self.is_edit_mode:
            self.username_input.setText(user_data.get("username", ""))
            self.password_input.setText(user_data.get("password", ""))
            self.role_combo.setCurrentText(user_data.get("role", "Standard"))
            if user_data.get("username") == "admin":
                self.username_input.setReadOnly(True)
                self.role_combo.setEnabled(False)

        form_layout.addRow("Потребителско име:", self.username_input)
        form_layout.addRow("Парола:", self.password_input)
        form_layout.addRow("Роля:", self.role_combo)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        main_layout.addLayout(form_layout)
        main_layout.addWidget(self.button_box)

    def get_data(self):
        return {
            "username": self.username_input.text().strip(),
            "password": self.password_input.text(),
            "role": self.role_combo.currentText()
        }