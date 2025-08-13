import cv2
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSlider
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap

from data_manager import get_translator
from ui_widgets import AspectRatioLabel

class MediaViewerDialog(QDialog):
    """
    Диалогов прозорец за преглед на снимки и видео записи с лента за превъртане.
    """
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.translator = get_translator()
        
        self.is_video = str(self.file_path).lower().endswith(('.mp4', '.avi', '.mov'))
        
        self.video_capture = None
        self.video_timer = QTimer(self)
        self.is_playing = False
        self.is_slider_pressed = False # Флаг, за да знаем кога потребителят мести лентата

        self.setWindowTitle(f"{self.translator.get_string('view_recording_button')}: {Path(self.file_path).name}")
        self.setMinimumSize(800, 600)

        main_layout = QVBoxLayout(self)
        
        self.media_label = AspectRatioLabel()
        self.media_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.media_label.setStyleSheet("background-color: black;")

        # --- ЛЕНТА ЗА ПРЕВЪРТАНЕ (SLIDER) ---
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setTracking(True)
        self.slider.sliderPressed.connect(self.slider_pressed)
        self.slider.sliderReleased.connect(self.slider_released)
        self.slider.sliderMoved.connect(self.seek_video)
        
        controls_layout = QHBoxLayout()
        self.play_pause_button = QPushButton()
        self.close_button = QPushButton("Затвори")

        controls_layout.addStretch()
        if self.is_video:
            controls_layout.addWidget(self.play_pause_button)
        controls_layout.addWidget(self.close_button)
        controls_layout.addStretch()

        main_layout.addWidget(self.media_label, 1)
        if self.is_video:
            main_layout.addWidget(self.slider) # Добавяме слайдера в лейаута
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
        self.video_capture = cv2.VideoCapture(str(self.file_path))
        if not self.video_capture.isOpened():
            self.media_label.setText("Грешка при зареждане на видео файла.")
            self.play_pause_button.setEnabled(False)
            self.slider.setEnabled(False)
            return
        
        fps = self.video_capture.get(cv2.CAP_PROP_FPS)
        total_frames = int(self.video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
        
        self.slider.setRange(0, total_frames - 1)
        
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
            current_frame = int(self.video_capture.get(cv2.CAP_PROP_POS_FRAMES))
            total_frames = int(self.video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
            if current_frame >= total_frames -1:
                self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)

            self.video_timer.start()
            self.is_playing = True
            self.play_pause_button.setText("Пауза")

    def display_next_frame(self):
        ret, frame = self.video_capture.read()
        if not ret:
            self.video_timer.stop()
            self.is_playing = False
            self.play_pause_button.setText(self.translator.get_string("replay_button"))
            return

        if not self.is_slider_pressed:
            current_frame = int(self.video_capture.get(cv2.CAP_PROP_POS_FRAMES))
            self.slider.setValue(current_frame)

        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        self.media_label.setPixmap(QPixmap.fromImage(qt_image))

    def slider_pressed(self):
        self.is_slider_pressed = True
        if self.is_playing:
            self.video_timer.stop()

    def slider_released(self):
        self.is_slider_pressed = False
        if self.is_playing:
            self.video_timer.start()

    def seek_video(self, frame_number):
        self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = self.video_capture.read()
        if ret:
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