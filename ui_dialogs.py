from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QVBoxLayout, QFormLayout, 
    QLineEdit, QCheckBox, QLabel, QComboBox, QTimeEdit, QGroupBox, QHBoxLayout
)
from PySide6.QtCore import QTime

from data_manager import get_translator

class CameraDialog(QDialog):
    def __init__(self, camera_data=None, parent=None):
        super().__init__(parent)
        self.is_edit_mode = camera_data is not None
        translator = get_translator()
        
        window_title_key = "edit_camera_title" if self.is_edit_mode else "add_camera_title"
        self.setWindowTitle(translator.get_string(window_title_key))
        self.setMinimumWidth(450)

        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.name_input = QLineEdit()
        self.url_input = QLineEdit()
        self.status_checkbox = QCheckBox(translator.get_string("active_checkbox"))
        self.motion_checkbox = QCheckBox(translator.get_string("motion_detection_checkbox"))

        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)

        # --- SCHEDULE UI ---
        schedule_group = QGroupBox(translator.get_string("recordings")) # Може да се добави по-добър ключ
        schedule_layout = QFormLayout(schedule_group)
        self.schedule_widgets = {}
        days = ["Понеделник", "Вторник", "Сряда", "Четвъртък", "Петък", "Събота", "Неделя"]
        
        for day in days:
            day_enabled = QCheckBox()
            start_time = QTimeEdit(QTime(0, 0))
            end_time = QTimeEdit(QTime(0, 0))
            
            time_layout = QHBoxLayout()
            time_layout.addWidget(QLabel("от:"))
            time_layout.addWidget(start_time)
            time_layout.addWidget(QLabel("до:"))
            time_layout.addWidget(end_time)
            
            schedule_layout.addRow(f"{day}:", day_enabled)
            schedule_layout.addRow("", time_layout)
            self.schedule_widgets[day] = (day_enabled, start_time, end_time)

        if self.is_edit_mode:
            self.name_input.setText(camera_data.get("name", ""))
            self.url_input.setText(camera_data.get("rtsp_url", ""))
            self.status_checkbox.setChecked(camera_data.get("is_active", True))
            self.motion_checkbox.setChecked(camera_data.get("motion_enabled", True))
            self.username_input.setText(camera_data.get("username", ""))
            self.password_input.setText(camera_data.get("password", ""))
            
            schedule_data = camera_data.get("schedule", {})
            for day, widgets in self.schedule_widgets.items():
                day_data = schedule_data.get(day, {"enabled": False, "start": "00:00", "end": "00:00"})
                widgets[0].setChecked(day_data["enabled"])
                widgets[1].setTime(QTime.fromString(day_data["start"], "HH:mm"))
                widgets[2].setTime(QTime.fromString(day_data["end"], "HH:mm"))
        else:
            self.status_checkbox.setChecked(True)
            self.motion_checkbox.setChecked(True)

        form_layout.addRow(translator.get_string("camera_name_label"), self.name_input)
        form_layout.addRow(translator.get_string("rtsp_address_label"), self.url_input)
        form_layout.addRow(translator.get_string("camera_username_label"), self.username_input)
        form_layout.addRow(translator.get_string("camera_password_label"), self.password_input)
        form_layout.addRow(self.status_checkbox)
        form_layout.addRow(self.motion_checkbox)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        main_layout.addLayout(form_layout)
        main_layout.addWidget(schedule_group)
        main_layout.addWidget(self.button_box)

    def get_data(self):
        schedule_data = {}
        for day, widgets in self.schedule_widgets.items():
            schedule_data[day] = {
                "enabled": widgets[0].isChecked(),
                "start": widgets[1].time().toString("HH:mm"),
                "end": widgets[2].time().toString("HH:mm")
            }
            
        return {
            "name": self.name_input.text().strip(),
            "rtsp_url": self.url_input.text().strip(),
            "is_active": self.status_checkbox.isChecked(),
            "motion_enabled": self.motion_checkbox.isChecked(),
            "username": self.username_input.text().strip(),
            "password": self.password_input.text(),
            "schedule": schedule_data
        }

class UserDialog(QDialog):
    """Диалогов прозорец за добавяне или редактиране на потребител."""
    def __init__(self, user_data=None, parent=None):
        super().__init__(parent)
        self.is_edit_mode = user_data is not None
        translator = get_translator()
        
        window_title_key = "edit_user_title" if self.is_edit_mode else "add_user_title"
        self.setWindowTitle(translator.get_string(window_title_key))
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

        form_layout.addRow(translator.get_string("username_label"), self.username_input)
        form_layout.addRow(translator.get_string("password_label"), self.password_input)
        form_layout.addRow(translator.get_string("role_label"), self.role_combo)

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