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
    FrameForRecording = Signal(object)

    def __init__(self, camera_data, recording_path):
        super().__init__()
        self.camera_data = camera_data
        self.rtsp_url = camera_data.get("rtsp_url")
        
        self.target_fps = 15
        self.frame_interval = 1.0 / self.target_fps
        self.frame_counter = 0

        self.motion_enabled = True 
        self.motion_sensitivity = 500

        self._is_running = True
        self._prev_frame_gray = None
        self.latest_frame = None
        self.frame_lock = threading.Lock()
        
        # --- ПРОМЯНА 1: Добавяме променлива за реалните FPS ---
        self.stream_fps = 20.0 # Стойност по подразбиране

    def run(self):
        self.StreamStatus.emit("Свързване...")
        cap = cv2.VideoCapture(self.rtsp_url)
        
        if not cap.isOpened():
            self.StreamStatus.emit("Грешка")
            return

        # --- ПРОМЯНА 2: Опитваме се да вземем реалните FPS от потока ---
        detected_fps = cap.get(cv2.CAP_PROP_FPS)
        if 0 < detected_fps < 100:  # Проверка за разумна стойност
            self.stream_fps = detected_fps
        print(f"Stream for {self.rtsp_url} opened with FPS: {self.stream_fps}")

        last_frame_time = time.time()

        while self._is_running:
            ret, frame = cap.read()
            if not ret:
                self.StreamStatus.emit("Прекъсване")
                break
            
            current_time = time.time()
            if current_time - last_frame_time < self.frame_interval:
                continue
            last_frame_time = current_time
            
            self.frame_counter += 1

            with self.frame_lock:
                self.latest_frame = frame.copy()
            
            self.FrameForRecording.emit(frame)
            
            if self.motion_enabled and self.frame_counter % 3 == 0:
                self.handle_motion_detection(frame)

            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            self.ImageUpdate.emit(qt_image)
            
        cap.release()
        print(f"Нишката за {self.rtsp_url} приключи.")

    def handle_motion_detection(self, frame):
        height, width, _ = frame.shape
        processing_width = 320 
        scale = processing_width / width
        new_width = processing_width
        new_height = int(height * scale)
        
        resized_frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)

        gray = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2GRAY)
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
    
    # --- ПРОМЯНА 3: Нов метод, който главният прозорец ще използва ---
    def get_stream_fps(self):
        """Връща определените кадри в секунда за този видео поток."""
        return self.stream_fps

    def get_latest_frame(self):
        with self.frame_lock:
            return self.latest_frame.copy() if self.latest_frame is not None else None

    def stop(self):
        self._is_running = False
        print(f"Подадена команда за спиране на нишката за {self.rtsp_url}")