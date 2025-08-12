import cv2
# --- ПРОМЯНА: Добавяме липсващия импорт за Path ---
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap

from data_manager import get_translator
from ui_widgets import AspectRatioLabel

class MediaViewerDialog(QDialog):
    """
    Диалогов прозорец за преглед на снимки и видео записи.
    """
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.translator = get_translator()
        
        self.is_video = str(self.file_path).lower().endswith(('.mp4', '.avi', '.mov'))
        
        # --- За видео ---
        self.video_capture = None
        self.video_timer = QTimer(self)
        self.is_playing = False

        self.setWindowTitle(f"{self.translator.get_string('view_recording_button')}: {Path(self.file_path).name}")
        self.setMinimumSize(800, 600)

        main_layout = QVBoxLayout(self)
        
        self.media_label = AspectRatioLabel()
        self.media_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.media_label.setStyleSheet("background-color: black;")
        
        controls_layout = QHBoxLayout()
        self.play_pause_button = QPushButton()
        self.close_button = QPushButton("Затвори")

        controls_layout.addStretch()
        if self.is_video:
            controls_layout.addWidget(self.play_pause_button)
        controls_layout.addWidget(self.close_button)
        controls_layout.addStretch()

        main_layout.addWidget(self.media_label, 1)
        main_layout.addLayout(controls_layout)

        self.close_button.clicked.connect(self.close)
        
        if self.is_video:
            self.play_pause_button.clicked.connect(self.toggle_play_pause)
            self.video_timer.timeout.connect(self.display_next_frame)
            self.load_video()
        else:
            self.load_image()

    def load_image(self):
        pixmap = QPixmap(self.file_path)
        self.media_label.setPixmap(pixmap)

    def load_video(self):
        self.video_capture = cv2.VideoCapture(str(self.file_path)) # cv2 работи по-добре със string
        if not self.video_capture.isOpened():
            self.media_label.setText("Грешка при зареждане на видео файла.")
            self.play_pause_button.setEnabled(False)
            return
        
        fps = self.video_capture.get(cv2.CAP_PROP_FPS)
        if fps > 0:
            self.video_timer.setInterval(int(1000 / fps))
        else:
            self.video_timer.setInterval(40)

        self.toggle_play_pause()

    def toggle_play_pause(self):
        if self.is_playing:
            self.video_timer.stop()
            self.is_playing = False
            self.play_pause_button.setText("Пусни")
        else:
            self.video_timer.start()
            self.is_playing = True
            self.play_pause_button.setText("Пауза")

    def display_next_frame(self):
        ret, frame = self.video_capture.read()
        if not ret:
            self.video_timer.stop()
            self.is_playing = False
            self.play_pause_button.setText("Пусни отново")
            self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            return

        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        self.media_label.setPixmap(QPixmap.fromImage(qt_image))

    def closeEvent(self, event):
        if self.video_timer.isActive():
            self.video_timer.stop()
        if self.video_capture:
            self.video_capture.release()
        super().closeEvent(event)