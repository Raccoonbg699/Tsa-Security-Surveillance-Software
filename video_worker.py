import cv2
import time
import uuid
from pathlib import Path
from datetime import datetime
from queue import Queue, Full, Empty
import threading
from PySide6.QtCore import QThread, Signal, QTimer, QTime
from PySide6.QtGui import QImage

class RecordingWorker(QThread):
    """
    "Умна" нишка за запис, която поддържа постоянен FPS чрез дублиране/пропускане на кадри.
    """
    def __init__(self, filename, width, height, fps):
        super().__init__()
        self.frame_queue = Queue(maxsize=10)
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
                frame = self.frame_queue.get(timeout=self.frame_duration)
                if frame is not None:
                    last_frame = frame
            except Empty:
                if not self._is_running:
                    break
            
            if last_frame is not None and self._video_writer.isOpened():
                current_time = time.time()
                while next_frame_time <= current_time:
                    try:
                        self._video_writer.write(last_frame)
                    except cv2.error as e:
                        print(f"Грешка при запис на кадър: {e}")
                    next_frame_time += self.frame_duration
        
        if self._video_writer.isOpened():
            self._video_writer.release()
        print("Нишката за запис приключи коректно.")

    # --- ПРОМЯНА: Методът вече приема два аргумента, за да съответства на сигнала ---
    def add_frame(self, cam_id, frame):
        if frame is not None:
            try:
                self.frame_queue.put_nowait(frame)
            except Full:
                pass

    def stop(self):
        self._is_running = False

class VideoWorker(QThread):
    ImageUpdate = Signal(str, QImage)
    StreamStatus = Signal(str, str)
    MotionDetected = Signal(str)
    FrameForRecording = Signal(str, object)
    
    def __init__(self, camera_data):
        super().__init__()
        self.camera_data = camera_data
        self.cam_id = self.camera_data.get("id")
        
        user = camera_data.get("username")
        pwd = camera_data.get("password")
        url = camera_data.get("rtsp_url", "")
        
        if user and pwd and "rtsp://" in url:
            url_parts = url.split("rtsp://")
            self.rtsp_url = f"rtsp://{user}:{pwd}@{url_parts[1]}"
        else:
            self.rtsp_url = url

        self.frame_queue = Queue(maxsize=2)
        self.motion_enabled = camera_data.get("motion_enabled", True)
        self.motion_sensitivity = 500
        self._is_running = True
        self._prev_frame_gray = None
        self.latest_frame = None
        self.frame_lock = threading.Lock()
        self.processing_thread = threading.Thread(target=self._process_frames, daemon=True)

    def run(self):
        self.StreamStatus.emit(self.cam_id, "Свързване...")
        cap = cv2.VideoCapture(self.rtsp_url)
        if not cap.isOpened():
            self.StreamStatus.emit(self.cam_id, "Грешка")
            self._is_running = False
            return
            
        self.StreamStatus.emit(self.cam_id, "Свързан")
        
        while self._is_running:
            ret, frame = cap.read()
            if not ret:
                self.StreamStatus.emit(self.cam_id, "Прекъсване")
                break
            try:
                self.frame_queue.put(frame, block=False)
            except Full:
                pass
            time.sleep(0.005)
        cap.release()
        self.frame_queue.put(None)
        print(f"Нишката за четене на {self.camera_data.get('name')} приключи.")

    def _process_frames(self):
        frame_counter = 0
        while self._is_running:
            frame = self.frame_queue.get()
            if frame is None: break
            with self.frame_lock:
                self.latest_frame = frame.copy()
            
            self.FrameForRecording.emit(self.cam_id, frame)
            
            display_frame = cv2.resize(frame, (1280, 720), interpolation=cv2.INTER_AREA)
            frame_counter += 1
            if self.motion_enabled and frame_counter % 3 == 0:
                self.handle_motion_detection(display_frame)
            rgb_image = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            self.ImageUpdate.emit(self.cam_id, qt_image)
        print(f"Нишката за обработка на {self.camera_data.get('name')} приключи.")

    def handle_motion_detection(self, processed_frame):
        gray = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2GRAY)
        if self._prev_frame_gray is None:
            self._prev_frame_gray = gray
            return
        frame_delta = cv2.absdiff(self._prev_frame_gray, gray)
        thresh = cv2.threshold(frame_delta, 30, 255, cv2.THRESH_BINARY)[1]
        motion_pixels = cv2.countNonZero(thresh)
        if motion_pixels > self.motion_sensitivity / 4: 
            self.MotionDetected.emit(self.cam_id)
        self._prev_frame_gray = gray

    def start(self):
        self._is_running = True
        self.processing_thread.start()
        super().start()

    def stop(self):
        print(f"Подадена команда за спиране на нишките за {self.camera_data.get('name')}")
        self._is_running = False
        if self.processing_thread.is_alive():
            self.processing_thread.join()

    def get_latest_frame(self):
        with self.frame_lock:
            return self.latest_frame.copy() if self.latest_frame is not None else None