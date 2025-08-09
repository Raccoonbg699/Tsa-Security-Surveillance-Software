from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QVBoxLayout, QFormLayout, 
    QLineEdit, QCheckBox, QLabel
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

        if self.is_edit_mode:
            self.name_input.setText(camera_data.get("name", ""))
            self.url_input.setText(camera_data.get("rtsp_url", ""))
            self.status_checkbox.setChecked(camera_data.get("is_active", True))
        else:
            self.status_checkbox.setChecked(True)

        form_layout.addRow("Име на камера:", self.name_input)
        form_layout.addRow("RTSP Адрес:", self.url_input)
        form_layout.addRow(self.status_checkbox)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        main_layout.addLayout(form_layout)
        main_layout.addWidget(self.button_box)

    def get_data(self):
        return {
            "name": self.name_input.text().strip(),
            "rtsp_url": self.url_input.text().strip(),
            "is_active": self.status_checkbox.isChecked()
        }