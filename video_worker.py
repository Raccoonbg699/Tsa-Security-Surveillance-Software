import cv2
import time
import uuid
from pathlib import Path
from datetime import datetime
from queue import Queue, Full
import threading
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

class RecordingWorker(QThread):
    """
    Отделна нишка, чиято единствена цел е да записва кадри на диска. (Непроменен)
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
    Вече управлява две вътрешни нишки: една за четене и една за обработка,
    за да не се блокира GUI интерфейсът.
    """
    ImageUpdate = Signal(QImage)
    StreamStatus = Signal(str)
    MotionDetected = Signal(str)
    FrameForRecording = Signal(object)

    def __init__(self, camera_data, recording_path):
        super().__init__()
        self.camera_data = camera_data
        self.rtsp_url = camera_data.get("rtsp_url")
        
        # Опашка с максимален размер 2, за да не се трупа закъснение
        self.frame_queue = Queue(maxsize=2)
        
        # Четем настройката за детекция от данните на камерата
        self.motion_enabled = camera_data.get("motion_enabled", True)
        self.motion_sensitivity = 500

        self._is_running = True
        self._prev_frame_gray = None
        self.latest_frame = None
        self.frame_lock = threading.Lock()
        self.stream_fps = 20.0
        
        # Нишката за обработка ще бъде стандартна Python нишка
        self.processing_thread = threading.Thread(target=self._process_frames, daemon=True)

    def run(self):
        """
        Този метод вече е само НИШКА ЗА ЧЕТЕНЕ.
        Основната му цел е да чете от камерата и да пълни опашката.
        """
        self.StreamStatus.emit("Свързване...")
        cap = cv2.VideoCapture(self.rtsp_url)
        
        if not cap.isOpened():
            self.StreamStatus.emit("Грешка")
            self._is_running = False
            return
            
        detected_fps = cap.get(cv2.CAP_PROP_FPS)
        if 0 < detected_fps < 100:
            self.stream_fps = detected_fps
        print(f"Stream for {self.rtsp_url} opened with FPS: {self.stream_fps}")

        while self._is_running:
            ret, frame = cap.read()
            if not ret:
                self.StreamStatus.emit("Прекъсване")
                break
            
            try:
                # Поставяме кадъра в опашката, без да чакаме (block=False)
                # Ако опашката е пълна, ще хвърли грешка Full, която хващаме
                self.frame_queue.put(frame, block=False)
            except Full:
                # Това е нормално поведение - просто пропускаме кадъра
                pass
            
            # Малка пауза, за да не товарим процесора излишно
            time.sleep(0.005)

        cap.release()
        # Поставяме None, за да сигнализираме на нишката за обработка да спре
        self.frame_queue.put(None) 
        print(f"Нишката за четене на {self.rtsp_url} приключи.")

    def _process_frames(self):
        """
        Този метод е НИШКАТА ЗА ОБРАБОТКА.
        Работи в отделна нишка и извършва тежките операции.
        """
        frame_counter = 0
        while self._is_running:
            # Взимаме кадър от опашката (чака, ако е празна)
            frame = self.frame_queue.get()
            
            # Ако получим None, спираме цикъла
            if frame is None:
                break
            
            frame_counter += 1

            with self.frame_lock:
                self.latest_frame = frame.copy()
            
            # Изпращаме всеки кадър за евентуален запис
            self.FrameForRecording.emit(frame)
            
            # Проверяваме дали изобщо трябва да правим детекция
            if self.motion_enabled and frame_counter % 3 == 0:
                self.handle_motion_detection(frame)

            # Конвертиране и изпращане към GUI
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            self.ImageUpdate.emit(qt_image)
        
        print(f"Нишката за обработка на {self.rtsp_url} приключи.")

    def start(self):
        self._is_running = True
        self.processing_thread.start() # Стартираме нишката за обработка
        super().start() # Стартираме QThread (нишката за четене)

    def stop(self):
        print(f"Подадена команда за спиране на нишките за {self.rtsp_url}")
        self._is_running = False
        # Изчакваме нишките да приключат
        if self.processing_thread.is_alive():
            self.processing_thread.join()

    def handle_motion_detection(self, frame):
        # ДРАСТИЧНА ОПТИМИЗАЦИЯ
        height, width, _ = frame.shape
        processing_width = 160 # Още по-малка резолюция
        scale = processing_width / width
        new_width = processing_width
        new_height = int(height * scale)
        
        resized_frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)

        gray = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2GRAY)
        
        # GaussianBlur е премахнат за максимално облекчение
        
        if self._prev_frame_gray is None:
            self._prev_frame_gray = gray
            return

        frame_delta = cv2.absdiff(self._prev_frame_gray, gray)
        thresh = cv2.threshold(frame_delta, 30, 255, cv2.THRESH_BINARY)[1] # Леко вдигнат праг
        motion_pixels = cv2.countNonZero(thresh)

        # Коригирана чувствителност
        if motion_pixels > self.motion_sensitivity / 4: 
            self.MotionDetected.emit(self.camera_data.get("id"))

        self._prev_frame_gray = gray
    
    def get_stream_fps(self):
        return self.stream_fps

    def get_latest_frame(self):
        with self.frame_lock:
            return self.latest_frame.copy() if self.latest_frame is not None else None