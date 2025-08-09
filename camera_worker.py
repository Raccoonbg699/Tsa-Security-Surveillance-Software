from PySide6.QtCore import QObject, Signal
# Други необходими импорти като cv2, threading и т.н. ще дойдат тук.

class Camera(QObject):
    # Сигналите и методите от стария Camera клас ще бъдат преместени тук.
    log_message = Signal(str)
    motion_detected = Signal()

    def __init__(self, name, rtsp_url, user, password):
        super().__init__()
        self.name = name
        self.rtsp_url = rtsp_url
        # ... и така нататък
    
    def start_stream(self):
        print(f"Starting stream for {self.name}")
        # Логиката ще бъде преместена тук.

    # ... останалите методи