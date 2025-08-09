from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QSizePolicy
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QPainter

class AspectRatioLabel(QLabel):
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
    double_clicked = Signal()

    def __init__(self, camera_name, camera_id):
        super().__init__()
        self.camera_name = camera_name
        self.camera_id = camera_id

        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
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

    def update_frame(self, q_image):
        self.video_label.setPixmap(QPixmap.fromImage(q_image))

    def update_status(self, status_text):
        self.video_label.setText(status_text)