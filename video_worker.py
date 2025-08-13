import cv2
import time
import uuid
from pathlib import Path
from datetime import datetime
from queue import Queue, Full
import threading
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

from data_manager import get_translator
from ui_widgets import AspectRatioLabel

class RecordingWorker(QThread):
    """
    "Умна" нишка за запис, която поддържа постоянен FPS чрез дублиране/пропускане на кадри.
    """
    def __init__(self, filename, width, height, fps):
        super().__init__()
        self.frame_queue = Queue()
        self._is_running = True
        self.target_fps = fps
        self.frame_duration = 1.0 / self.target_fps
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self._video_writer = cv2.VideoWriter(str(filename), fourcc, self.target_fps, (width, height))

    def run(self):
        last_frame = None
        next_frame_time = time.time()

        while self._is_running or not self.frame_queue.empty():
            try:
                # Взимаме кадър, но не чакаме повече от необходимото
                frame = self.frame_queue.get(timeout=self.frame_duration)
                last_frame = frame
            except Exception:
                # Ако няма нов кадър, просто продължаваме да записваме стария
                if not self._is_running:
                    break # Излизаме, ако е спряна и опашката е празна
            
            # Ако имаме кадър, го записваме, докато наваксаме с времето
            if last_frame is not None and self._video_writer.isOpened():
                current_time = time.time()
                while next_frame_time <= current_time:
                    self._video_writer.write(last_frame)
                    next_frame_time += self.frame_duration
        
        if self._video_writer.isOpened():
            self._video_writer.release()
        print("Нишката за запис приключи коректно.")

    def add_frame(self, frame):
        # Опашката вече не трябва да е голяма
        if self.frame_queue.qsize() < 2:
            self.frame_queue.put(frame)

    def stop(self):
        self._is_running = False

class VideoWorker(QThread):
    ImageUpdate = Signal(QImage)
    StreamStatus = Signal(str)
    MotionDetected = Signal(str)
    FrameForRecording = Signal(object) # Вече изпраща само кадъра

    def __init__(self, camera_data, recording_path):
        super().__init__()
        self.camera_data = camera_data
        self.rtsp_url = camera_data.get("rtsp_url")
        self.frame_queue = Queue(maxsize=2)
        self.motion_enabled = camera_data.get("motion_enabled", True)
        self.motion_sensitivity = 500
        self._is_running = True
        self._prev_frame_gray = None
        self.latest_frame = None
        self.frame_lock = threading.Lock()
        self.processing_thread = threading.Thread(target=self._process_frames, daemon=True)

    def run(self):
        self.StreamStatus.emit("Свързване...")
        cap = cv2.VideoCapture(self.rtsp_url)
        if not cap.isOpened():
            self.StreamStatus.emit("Грешка")
            self._is_running = False
            return
        while self._is_running:
            ret, frame = cap.read()
            if not ret:
                self.StreamStatus.emit("Прекъсване")
                break
            try:
                self.frame_queue.put(frame, block=False)
            except Full:
                pass
            time.sleep(0.005)
        cap.release()
        self.frame_queue.put(None)
        print(f"Нишката за четене на {self.rtsp_url} приключи.")

    def _process_frames(self):
        frame_counter = 0
        while self._is_running:
            frame = self.frame_queue.get()
            if frame is None: break
            with self.frame_lock:
                self.latest_frame = frame.copy()
            
            # Изпращаме само кадъра, без времева марка
            self.FrameForRecording.emit(frame)
            
            display_frame = cv2.resize(frame, (1280, 720), interpolation=cv2.INTER_AREA)
            frame_counter += 1
            if self.motion_enabled and frame_counter % 3 == 0:
                self.handle_motion_detection(display_frame)
            rgb_image = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            self.ImageUpdate.emit(qt_image)
        print(f"Нишката за обработка на {self.rtsp_url} приключи.")

    def handle_motion_detection(self, processed_frame):
        gray = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2GRAY)
        if self._prev_frame_gray is None:
            self._prev_frame_gray = gray
            return
        frame_delta = cv2.absdiff(self._prev_frame_gray, gray)
        thresh = cv2.threshold(frame_delta, 30, 255, cv2.THRESH_BINARY)[1]
        motion_pixels = cv2.countNonZero(thresh)
        if motion_pixels > self.motion_sensitivity / 4: 
            self.MotionDetected.emit(self.camera_data.get("id"))
        self._prev_frame_gray = gray

    def start(self):
        self._is_running = True
        self.processing_thread.start()
        super().start()
    def stop(self):
        print(f"Подадена команда за спиране на нишките за {self.rtsp_url}")
        self._is_running = False
        if self.processing_thread.is_alive():
            self.processing_thread.join()
    def get_latest_frame(self):
        with self.frame_lock:
            return self.latest_frame.copy() if self.latest_frame is not None else None