import cv2
import queue
from PySide6.QtCore import QThread, Signal, QTimer
from PySide6.QtGui import QImage
from data_manager import DataManager
from datetime import datetime
import numpy as np

class VideoWorker(QThread):
    ImageUpdate = Signal(str, QImage)
    StreamStatus = Signal(str, str)
    FrameForRecording = Signal(str, object)
    MotionDetected = Signal(str)

    def __init__(self, camera_data):
        super().__init__()
        self.camera_data = camera_data
        self.camera_id = camera_data.get("id")
        self.rtsp_url = camera_data.get("rtsp_url")
        self._run_flag = True
        self.latest_frame = None
        self.last_frame_time = datetime.now()
        
        self.reconnect_timer = QTimer()
        self.reconnect_timer.setSingleShot(True)
        self.reconnect_timer.timeout.connect(self.start)
        self.moveToThread(self)

        # Засичане на движение
        self.motion_enabled = camera_data.get("motion_enabled", False)
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=50, detectShadows=False)
        self.last_motion_time = None
        self.motion_cooldown = 5 # секунди

    def run(self):
        self._run_flag = True
        cap = cv2.VideoCapture(self.rtsp_url)
        
        if not cap.isOpened():
            self.StreamStatus.emit(self.camera_id, "Грешка при свързване")
            return

        self.StreamStatus.emit(self.camera_id, "Свързан")

        while self._run_flag:
            ret, frame = cap.read()
            if not ret:
                self.StreamStatus.emit(self.camera_id, "Прекъсната връзка")
                break
            
            self.last_frame_time = datetime.now()
            self.latest_frame = frame.copy()

            if self.motion_enabled:
                self.detect_motion(frame)

            self.FrameForRecording.emit(self.camera_id, frame)
            
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_BGR888)
            self.ImageUpdate.emit(self.camera_id, qt_image)
        
        cap.release()
        if self._run_flag:
            print(f"Връзката с камера {self.camera_id} е загубена. Опит за повторно свързване след 5 секунди...")
            self.StreamStatus.emit(self.camera_id, "Повторно свързване...")

    def detect_motion(self, frame):
        fg_mask = self.bg_subtractor.apply(frame)
        
        # Праг за премахване на шума
        thresh = cv2.threshold(fg_mask, 25, 255, cv2.THRESH_BINARY)[1]
        
        # Разширяване, за да се запълнят дупките
        dilated = cv2.dilate(thresh, None, iterations=2)
        
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        motion_detected_this_frame = False
        for contour in contours:
            if cv2.contourArea(contour) < 500: # Минимална площ за засичане
                continue
            
            motion_detected_this_frame = True
            break
        
        now = datetime.now()
        if motion_detected_this_frame:
            if self.last_motion_time is None or (now - self.last_motion_time).total_seconds() > self.motion_cooldown:
                print(f"Движение засечено от {self.camera_data.get('name')}")
                self.last_motion_time = now
                self.MotionDetected.emit(self.camera_id)

    def get_latest_frame(self):
        if (datetime.now() - self.last_frame_time).total_seconds() > 5:
            return None
        return self.latest_frame

    def stop(self):
        self._run_flag = False

class RecordingWorker(QThread):
    def __init__(self, filename, width, height, fps):
        super().__init__()
        self._run_flag = True
        self.filename = filename
        self.frame_queue = queue.Queue(maxsize=100)
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.writer = cv2.VideoWriter(filename, fourcc, fps, (width, height))

    def run(self):
        expected_width = int(self.writer.get(cv2.CAP_PROP_FRAME_WIDTH))
        expected_height = int(self.writer.get(cv2.CAP_PROP_FRAME_HEIGHT))

        while self._run_flag or not self.frame_queue.empty():
            try:
                frame = self.frame_queue.get(timeout=1)
                if frame is not None:
                    # Проверка за съвпадение на размерите
                    if frame.shape[1] != expected_width or frame.shape[0] != expected_height:
                        # Преоразмеряване на кадъра до очаквания размер
                        frame = cv2.resize(frame, (expected_width, expected_height))
                    
                    self.writer.write(frame)
            except queue.Empty:
                continue
        self.writer.release()
        print(f"Записът е запазен в {self.filename}")

    def add_frame(self, frame):
        if not self.frame_queue.full():
            self.frame_queue.put(frame)

    def stop(self):
        self._run_flag = False