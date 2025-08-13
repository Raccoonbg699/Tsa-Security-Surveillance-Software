import os
import datetime
import cv2
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLabel, QLineEdit,
    QPushButton, QHBoxLayout, QDialogButtonBox
)
from PySide6.QtCore import Qt

from data_manager import get_translator

class InfoDialog(QDialog):
    """
    Диалогов прозорец за показване на детайлна информация за файл.
    """
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.translator = get_translator()
        self.file_path_obj = Path(file_path)

        self.setWindowTitle("Информация за файла")
        self.setMinimumWidth(500)

        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # Извличане на информацията за файла
        file_name = self.file_path_obj.name
        file_size_bytes = os.path.getsize(self.file_path_obj)
        file_size_mb = file_size_bytes / (1024 * 1024)
        creation_timestamp = os.path.getctime(self.file_path_obj)
        creation_datetime = datetime.datetime.fromtimestamp(creation_timestamp).strftime('%Y-%m-%d %H:%M:%S')
        full_path = str(self.file_path_obj)
        
        duration_str = "N/A"
        if file_name.lower().endswith(('.mp4', '.avi', '.mov')):
            duration_str = self.get_video_duration()

        # Създаване на полета, които не могат да се редактират
        name_field = QLineEdit(file_name)
        name_field.setReadOnly(True)
        size_field = QLineEdit(f"{file_size_mb:.2f} MB")
        size_field.setReadOnly(True)
        duration_field = QLineEdit(duration_str)
        duration_field.setReadOnly(True)
        created_field = QLineEdit(creation_datetime)
        created_field.setReadOnly(True)
        path_field = QLineEdit(full_path)
        path_field.setReadOnly(True)

        form_layout.addRow("Име на файла:", name_field)
        form_layout.addRow("Размер:", size_field)
        form_layout.addRow("Дължина:", duration_field)
        form_layout.addRow("Дата на създаване:", created_field)
        form_layout.addRow("Местоположение:", path_field)
        
        # Бутон за затваряне
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        button_box.accepted.connect(self.accept)

        main_layout.addLayout(form_layout)
        main_layout.addWidget(button_box)

    def get_video_duration(self):
        """Изчислява дължината на видео файл."""
        try:
            cap = cv2.VideoCapture(str(self.file_path_obj))
            if not cap.isOpened():
                return "00:00:00"
            
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            if fps > 0 and frame_count > 0:
                total_seconds = int(frame_count / fps)
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                seconds = total_seconds % 60
                cap.release()
                return f"{hours:02}:{minutes:02}:{seconds:02}"
            else:
                cap.release()
                return "00:00:00"
        except Exception as e:
            print(f"Грешка при извличане на дължина на видео: {e}")
            return "00:00:00"