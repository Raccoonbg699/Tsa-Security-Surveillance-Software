import cv2
import time
import uuid
from pathlib import Path
from datetime import datetime
from queue import Queue
import threading
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

class RecordingWorker(QThread):
    """
    Отделна нишка, чиято единствена цел е да записва кадри на диска.
    """
    def __init__(self, filename, width, height, fps):
        super().__init__()
        self.frame_queue = Queue()
        self._is_running = True
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self._video_writer = cv2.VideoWriter(str(filename), fourcc, fps, (width, height))

    def run(self):
        while self._is_running or not self.frame_queue.empty():
            try:
                frame = self.frame_queue.get(timeout=1)
                if self._video_writer.isOpened():
                    self._video_writer.write(frame)
            except Exception:
                break
        
        if self._video_writer.isOpened():
            self._video_writer.release()
        print("Нишката за запис приключи коректно.")

    def add_frame(self, frame):
        self.frame_queue.put(frame)

    def stop(self):
        self._is_running = False

class VideoWorker(QThread):
    """
    Тази нишка вече само чете видео и го показва. НЕ записва.
    """
    ImageUpdate = Signal(QImage)
    StreamStatus = Signal(str)
    MotionDetected = Signal(str)
    # --- ТУК Е ЛИПСВАЩИЯТ СИГНАЛ ---
    FrameForRecording = Signal(object)

    def __init__(self, camera_data, recording_path):
        super().__init__()
        self.camera_data = camera_data
        self.rtsp_url = camera_data.get("rtsp_url")
        
        self.motion_enabled = True 
        self.motion_sensitivity = 500

        self._is_running = True
        self._prev_frame_gray = None
        self.latest_frame = None
        self.frame_lock = threading.Lock()

    def run(self):
        self.StreamStatus.emit("Свързване...")
        cap = cv2.VideoCapture(self.rtsp_url)
        
        if not cap.isOpened():
            self.StreamStatus.emit("Грешка")
            return

        while self._is_running:
            ret, frame = cap.read()
            if not ret:
                self.StreamStatus.emit("Прекъсване")
                break
            
            with self.frame_lock:
                self.latest_frame = frame.copy()
            
            # Изпращаме копие на кадъра за запис
            self.FrameForRecording.emit(frame)
            
            if self.motion_enabled:
                self.handle_motion_detection(frame)

            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            self.ImageUpdate.emit(qt_image)
            
        cap.release()
        print(f"Нишката за {self.rtsp_url} приключи.")

    def handle_motion_detection(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if self._prev_frame_gray is None:
            self._prev_frame_gray = gray
            return

        frame_delta = cv2.absdiff(self._prev_frame_gray, gray)
        thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
        motion_pixels = cv2.countNonZero(thresh)

        if motion_pixels > self.motion_sensitivity:
            self.MotionDetected.emit(self.camera_data.get("id"))

        self._prev_frame_gray = gray

    def get_latest_frame(self):
        with self.frame_lock:
            return self.latest_frame.copy() if self.latest_frame is not None else None

    def stop(self):
        self._is_running = False
        print(f"Подадена команда за спиране на нишката за {self.rtsp_url}")