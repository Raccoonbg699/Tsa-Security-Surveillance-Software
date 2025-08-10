from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QSizePolicy
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QPixmap, QPainter

class AspectRatioLabel(QLabel):
    """QLabel, който запазва пропорциите на изображението."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMinimumSize(1, 1)
        self._pixmap = QPixmap()

    def setPixmap(self, pixmap):
        if pixmap and not pixmap.isNull():
            self._pixmap = pixmap
            self.update()

    def paintEvent(self, event):
        if self._pixmap.isNull():
            super().paintEvent(event)
            return
        
        scaled_pixmap = self._pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        point = self.rect().center() - scaled_pixmap.rect().center()
        painter = QPainter(self)
        painter.drawPixmap(point, scaled_pixmap)

class VideoFrame(QFrame):
    """Уиджет, който показва видео поток от една камера."""
    double_clicked = Signal()

    def __init__(self, camera_name, camera_id):
        super().__init__()
        self.camera_name = camera_name
        self.camera_id = camera_id
        self._is_recording = False
        self._is_motion = False

        # --- ТУК Е КЛЮЧОВАТА ПОПРАВКА ---
        # Създаваме таймера като част от този обект. Когато обектът се изтрие, и таймерът изчезва.
        self.motion_timer = QTimer(self)
        self.motion_timer.setSingleShot(True)
        self.motion_timer.timeout.connect(lambda: self.set_motion_state(False))

        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        self.setStyleSheet("QFrame { border: 2px solid #3E3E42; }")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.video_label = AspectRatioLabel("Свързване...")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet("background-color: black;")
        
        self.name_label = QLabel(self.camera_name)
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setStyleSheet("background-color: rgba(0, 0, 0, 0.6); color: white; padding: 4px;")

        layout.addWidget(self.video_label, 1)
        layout.addWidget(self.name_label)

    def mouseDoubleClickEvent(self, event):
        self.double_clicked.emit()
        super().mouseDoubleClickEvent(event)
        
    def set_recording_state(self, is_recording):
        self._is_recording = is_recording
        self.update_border_color()

    def set_motion_state(self, is_motion):
        self._is_motion = is_motion
        self.update_border_color()
        if is_motion:
            # Стартираме нашия сигурен, вграден таймер
            self.motion_timer.start(1000)
    
    def update_border_color(self):
        if self._is_recording:
            self.setStyleSheet("QFrame { border: 2px solid #D13438; }")
        elif self._is_motion:
            self.setStyleSheet("QFrame { border: 2px solid #E81123; }")
        else:
            self.setStyleSheet("QFrame { border: 2px solid #3E3E42; }")

    def update_frame(self, q_image):
        self.video_label.setPixmap(QPixmap.fromImage(q_image))

    def update_status(self, status_text):
        self.video_label.setText(status_text)