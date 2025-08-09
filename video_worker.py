import cv2
import time
from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtGui import QImage

class VideoWorker(QThread):
    ImageUpdate = Signal(QImage)
    StreamStatus = Signal(str)

    def __init__(self, rtsp_url):
        super().__init__()
        self.rtsp_url = rtsp_url
        self._is_running = True

    def run(self):
        cap = cv2.VideoCapture(self.rtsp_url)
        if not cap.isOpened():
            self.StreamStatus.emit("Грешка при свързване")
            return

        self.StreamStatus.emit("Свързан")
        while self._is_running:
            ret, frame = cap.read()
            if ret:
                rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_image.shape
                bytes_per_line = ch * w
                qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                self.ImageUpdate.emit(qt_image)
            else:
                self.StreamStatus.emit("Връзката е загубена")
                cap.release()
                time.sleep(5)
                if not self._is_running: break
                cap = cv2.VideoCapture(self.rtsp_url)
                if not cap.isOpened():
                    self.StreamStatus.emit("Грешка при пресвързване")
                    break

        cap.release()
        print(f"Нишката за {self.rtsp_url} приключи.")

    def stop(self):
        self._is_running = False
        self.quit()
        self.wait()