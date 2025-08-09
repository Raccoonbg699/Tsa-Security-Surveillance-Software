import sys
import cv2
import socket
import threading
import time
import json
import os
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
from ipaddress import ip_network, ip_address, IPv4Network
from urllib.parse import urlparse

# Опит за импортиране на ONVIF библиотека. Ако я няма, PTZ няма да работи.
try:
    from onvif import ONVIFCamera
    ONVIF_ENABLED = True
except ImportError:
    ONVIF_ENABLED = False

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QListWidgetItem, QGridLayout, QFrame,
    QInputDialog, QDialog, QFormLayout, QLineEdit, QDialogButtonBox,
    QSlider, QAbstractItemView, QProgressDialog, QSizePolicy, QTabWidget,
    QFileSystemModel, QTreeView, QSplitter, QMessageBox, QCheckBox
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread, QDir, QRect
from PyQt5.QtGui import QFont, QImage, QPixmap, QPainter, QPen

# --- Глобални настройки ---
APP_NAME = "TSA-Security"
USER_VIDEOS_DIR = Path.home() / "Videos"
APP_DIR = USER_VIDEOS_DIR / APP_NAME
CONFIG_FILE = APP_DIR / "config.json"

# --- Създаване на необходимите директории ---
APP_DIR.mkdir(exist_ok=True, parents=True)

# --- Цветова палитра и стилове ---
DARK_BG_COLOR = "#252526"
MEDIUM_BG_COLOR = "#2D2D30"
LIGHT_FG_COLOR = "#CCCCCC"
ACCENT_COLOR = "#007ACC"
ACCENT_HOVER_COLOR = "#0099E6"
BORDER_COLOR = "#3E3E42"
ERROR_COLOR = "#F44747"
RECORDING_COLOR = "#D13438"
MOTION_COLOR = "#E81123"

STYLESHEET = f"""
    QMainWindow, QDialog, QProgressDialog {{
        background-color: {DARK_BG_COLOR}; color: {LIGHT_FG_COLOR}; font-family: Arial;
    }}
    QProgressDialog QLabel {{ color: {LIGHT_FG_COLOR}; }}
    QFrame {{
        border: 1px solid {BORDER_COLOR}; border-radius: 4px; background-color: {DARK_BG_COLOR};
    }}
    QLabel {{ color: {LIGHT_FG_COLOR}; font-size: 14px; }}
    QPushButton {{
        background-color: {ACCENT_COLOR}; color: white; border: none;
        padding: 8px 16px; font-size: 14px; border-radius: 4px;
    }}
    QPushButton:hover {{ background-color: {ACCENT_HOVER_COLOR}; }}
    QPushButton:disabled {{ background-color: {BORDER_COLOR}; color: #888888; }}
    QLineEdit, QListWidget, QTreeView, QCheckBox {{
        background-color: {MEDIUM_BG_COLOR}; border: 1px solid {BORDER_COLOR};
        border-radius: 4px; padding: 5px; color: {LIGHT_FG_COLOR}; font-size: 14px;
    }}
    QListWidget::item, QTreeView::item {{ padding: 8px; }}
    QListWidget::item:selected, QTreeView::item:selected {{ background-color: {ACCENT_COLOR}; color: white; }}
    QHeaderView::section {{ background-color: {MEDIUM_BG_COLOR}; padding: 4px; border: 1px solid {BORDER_COLOR}; }}
    QTabWidget::pane {{ border: 1px solid {BORDER_COLOR}; }}
    QTabBar::tab {{
        background: {MEDIUM_BG_COLOR}; color: {LIGHT_FG_COLOR}; padding: 10px;
        border: 1px solid {BORDER_COLOR}; border-bottom: none; border-top-left-radius: 4px; border-top-right-radius: 4px;
    }}
    QTabBar::tab:selected {{ background: {DARK_BG_COLOR}; }}
"""

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
        scaled_pixmap = self._pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        point = self.rect().center() - scaled_pixmap.rect().center()
        painter = QPainter(self)
        painter.drawPixmap(point, scaled_pixmap)


class CameraDialog(QDialog):
    def __init__(self, camera_data=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Camera" if camera_data else "Add New Camera")
        self.layout = QFormLayout(self)
        self.name_input = QLineEdit()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("rtsp://192.168.1.10:554/stream1")
        self.user_input = QLineEdit()
        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.Password)
        self.layout.addRow("Camera Name:", self.name_input)
        self.layout.addRow("RTSP URL:", self.url_input)
        self.layout.addRow("Username (for PTZ):", self.user_input)
        self.layout.addRow("Password (for PTZ):", self.pass_input)
        if camera_data:
            self.name_input.setText(camera_data.get("name", ""))
            self.url_input.setText(camera_data.get("url", ""))
            self.user_input.setText(camera_data.get("user", ""))
            self.pass_input.setText(camera_data.get("pass", ""))
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.layout.addWidget(self.buttons)

    def get_data(self):
        return {"name": self.name_input.text(), "url": self.url_input.text(), "user": self.user_input.text(), "pass": self.pass_input.text()}


class Camera(QObject):
    log_message = pyqtSignal(str)
    motion_detected = pyqtSignal()
    motion_stopped = pyqtSignal()

    def __init__(self, name, rtsp_url, user, password, motion_config=None):
        super().__init__()
        self.name = name
        self.rtsp_url = rtsp_url
        self.user = user
        self.password = password
        if motion_config is None: motion_config = {}
        self.motion_enabled = motion_config.get("enabled", False)
        self.motion_sensitivity = motion_config.get("sensitivity", 500)
        self.roi = motion_config.get("roi", None)
        self.post_motion_record_time = motion_config.get("post_motion_time", 5)
        
        self.is_running = False
        self.thread = None
        self.latest_frame = None
        self.lock = threading.Lock()
        self.is_manual_recording = False
        self.is_motion_recording = False
        self.video_writer = None
        self.onvif_cam = None
        self.ptz_service = None
        self.media_profile = None
        self.camera_dir = APP_DIR / self.name
        self.camera_dir.mkdir(exist_ok=True)
        self._prev_frame_gray = None
        self._last_motion_time = 0
        
    def get_motion_config(self):
        return {"enabled": self.motion_enabled, "sensitivity": self.motion_sensitivity, "roi": self.roi, "post_motion_time": self.post_motion_record_time}

    def update_details(self, name, rtsp_url, user, password):
        old_dir = self.camera_dir
        self.name = name
        self.rtsp_url = rtsp_url
        self.user = user
        self.password = password
        new_camera_dir = APP_DIR / self.name
        if old_dir != new_camera_dir and old_dir.exists():
            try:
                shutil.move(str(old_dir), str(new_camera_dir))
                self.camera_dir = new_camera_dir
            except Exception as e:
                self.log_message.emit(f"Could not rename directory {old_dir} to {new_camera_dir}: {e}")
                self.camera_dir = new_camera_dir
        self.camera_dir.mkdir(exist_ok=True)

    def start_stream(self):
        if self.is_running: return True
        self.is_running = True
        self.thread = threading.Thread(target=self._read_stream, daemon=True)
        self.thread.start()
        time.sleep(1)
        return self.is_running

    def stop_stream(self):
        if not self.is_running: return
        self.is_running = False
        if self.thread: self.thread.join(timeout=2)

    def _read_stream(self):
        cap = cv2.VideoCapture(self.rtsp_url)
        if not cap.isOpened():
            self.log_message.emit(f"[{self.name}] Failed to open stream with OpenCV.")
            self.is_running = False
            return
            
        self.log_message.emit(f"[{self.name}] Stream opened successfully with OpenCV.")
        self.initialize_onvif()

        while self.is_running and cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                self.log_message.emit(f"[{self.name}] Lost connection or stream ended.")
                break
            
            self.handle_motion_detection(frame)

            with self.lock:
                self.latest_frame = frame
                if (self.is_manual_recording or self.is_motion_recording) and self.video_writer:
                    self.video_writer.write(frame)
        
        self.is_running = False
        if self.is_manual_recording or self.is_motion_recording: self.stop_recording()
        cap.release()

    def handle_motion_detection(self, frame):
        if not self.motion_enabled: return
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        if self._prev_frame_gray is None:
            self._prev_frame_gray = gray
            return
        frame_delta = cv2.absdiff(self._prev_frame_gray, gray)
        thresh = cv2.threshold(frame_delta, 25, 255, cv2.THRESH_BINARY)[1]
        if self.roi:
            x, y, w, h = self.roi
            mask = thresh[y:y+h, x:x+w]
            motion_pixels = cv2.countNonZero(mask)
        else:
            motion_pixels = cv2.countNonZero(thresh)
        if motion_pixels > self.motion_sensitivity:
            self._last_motion_time = time.time()
            if not self.is_motion_recording:
                self.is_motion_recording = True
                self.start_recording(is_motion=True)
                self.motion_detected.emit()
        else:
            if self.is_motion_recording and (time.time() - self._last_motion_time > self.post_motion_record_time):
                self.is_motion_recording = False
                self.stop_recording()
                self.motion_stopped.emit()
        self._prev_frame_gray = gray

    def initialize_onvif(self):
        if not ONVIF_ENABLED or not self.user:
            self.log_message.emit(f"[{self.name}] ONVIF disabled or no credentials. PTZ will not work.")
            return
        try:
            parsed_url = urlparse(self.rtsp_url)
            ip = parsed_url.hostname
            if not ip:
                self.log_message.emit(f"[{self.name}] Could not parse IP from RTSP URL. PTZ will not work.")
                return
            self.log_message.emit(f"[{self.name}] Initializing ONVIF for PTZ on {ip}...")
            self.onvif_cam = ONVIFCamera(ip, 80, self.user, self.password)
            self.log_message.emit(f"[{self.name}] Creating PTZ service...")
            self.ptz_service = self.onvif_cam.create_ptz_service()
            self.log_message.emit(f"[{self.name}] Getting media profiles...")
            profiles = self.onvif_cam.get_profiles()
            if not profiles:
                self.log_message.emit(f"[{self.name}] No media profiles found. PTZ will not work.")
                self.ptz_service = None
                return
            self.media_profile = profiles[0]
            if not self.media_profile.PTZConfiguration:
                self.log_message.emit(f"[{self.name}] No PTZ configuration in media profile. PTZ not supported.")
                self.ptz_service = None
                return
            self.log_message.emit(f"[{self.name}] ONVIF Initialized Successfully.")
        except Exception as e:
            self.log_message.emit(f"[{self.name}] ONVIF Initialization Failed: {e}")
            self.onvif_cam = None
            self.ptz_service = None

    def ptz_move(self, pan=0.0, tilt=0.0, zoom=0.0):
        if not self.ptz_service: return
        try:
            request = self.ptz_service.create_type('ContinuousMove')
            request.ProfileToken = self.media_profile.token
            request.Velocity = {'PanTilt': {'x': pan, 'y': tilt}, 'Zoom': {'x': zoom}}
            self.ptz_service.ContinuousMove(request)
        except Exception as e:
            self.log_message.emit(f"[{self.name}] PTZ Move Error: {e}")

    def ptz_stop(self):
        if not self.ptz_service: return
        try:
            self.ptz_service.Stop({'ProfileToken': self.media_profile.token})
        except Exception as e:
            self.log_message.emit(f"[{self.name}] PTZ Stop Error: {e}")

    def get_frame(self):
        with self.lock: return self.latest_frame

    def take_snapshot(self):
        with self.lock:
            if self.latest_frame is None: return None
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = self.camera_dir / f"snap_{timestamp}.jpg"
            cv2.imwrite(str(filename), self.latest_frame)
            return filename

    def start_recording(self, is_motion=False):
        with self.lock:
            if self.video_writer or self.latest_frame is None: return False
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            prefix = "motion" if is_motion else "rec"
            filename = self.camera_dir / f"{prefix}_{timestamp}.mp4"
            
            try:
                h, w, _ = self.latest_frame.shape
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                temp_cap = cv2.VideoCapture(self.rtsp_url)
                fps = temp_cap.get(cv2.CAP_PROP_FPS)
                temp_cap.release()
                if fps == 0.0: fps = 25.0

                self.video_writer = cv2.VideoWriter(str(filename), fourcc, fps, (w, h))
                self.log_message.emit(f"[{self.name}] Recording started: {filename.name}")
                return True
            except Exception as e:
                self.log_message.emit(f"[{self.name}] Failed to start recording: {e}")
                if self.video_writer: self.video_writer.release()
                self.video_writer = None
                return False

    def stop_recording(self):
        with self.lock:
            if not self.video_writer: return
            self.log_message.emit(f"[{self.name}] Recording stopped.")
            self.video_writer.release()
            self.video_writer = None

# ... (Останалите класове остават същите)
class PTZButton(QPushButton):
    pressed = pyqtSignal()
    released = pyqtSignal()
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton: self.pressed.emit()
        super().mousePressEvent(event)
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton: self.released.emit()
        super().mouseReleaseEvent(event)

class NetworkScanner(QObject):
    camera_found = pyqtSignal(str)
    scan_progress = pyqtSignal(int)
    scan_finished = pyqtSignal(str)
    def __init__(self, subnet):
        super().__init__()
        self.subnet = subnet
        self.is_cancelled = False
    def run(self):
        try:
            hosts = list(self.subnet.hosts())
            total_hosts = len(hosts)
            for i, ip in enumerate(hosts):
                if self.is_cancelled: break
                ip_str = str(ip)
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(0.1)
                    if sock.connect_ex((ip_str, 554)) == 0:
                        self.camera_found.emit(ip_str)
                self.scan_progress.emit(int(((i + 1) / total_hosts) * 100))
            self.scan_finished.emit("Scan cancelled." if self.is_cancelled else "Network scan finished.")
        except Exception as e:
            self.scan_finished.emit(f"Scan error: {e}")
    def cancel(self): self.is_cancelled = True

class VideoFrame(QFrame):
    frame_clicked = pyqtSignal(object)
    roi_defined = pyqtSignal(QRect)
    def __init__(self, camera):
        super().__init__()
        self.camera = camera
        self.is_selected = False
        self.is_defining_roi = False
        self.roi_rect = None
        self.temp_roi_rect = None
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.video_label = AspectRatioLabel("Connecting...")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setFont(QFont("Arial", 12))
        self.name_label = QLabel(self.camera.name)
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setStyleSheet("background-color: rgba(0,0,0,0.5); padding: 4px; color: white;")
        layout.addWidget(self.video_label, 1)
        layout.addWidget(self.name_label)
        layout.setStretch(0, 1)
        layout.setStretch(1, 0)
        self.set_selected(False)

    def set_selected(self, selected):
        self.is_selected = selected
        if self.is_motion_detected():
            style = f"border: 2px solid {MOTION_COLOR};"
        elif selected:
            style = f"border: 2px solid {ACCENT_COLOR};"
        else:
            style = f"border: 1px solid {BORDER_COLOR};"
        self.setStyleSheet(style + f"border-radius: 4px; background-color: {DARK_BG_COLOR};")

    def is_motion_detected(self):
        return self.camera.is_motion_recording

    def mousePressEvent(self, event):
        if self.is_defining_roi and event.button() == Qt.LeftButton:
            self.temp_roi_rect = QRect(event.pos(), event.pos())
            self.update()
        else:
            self.frame_clicked.emit(self)
    
    def mouseMoveEvent(self, event):
        if self.is_defining_roi and self.temp_roi_rect:
            self.temp_roi_rect.setBottomRight(event.pos())
            self.update()

    def mouseReleaseEvent(self, event):
        if self.is_defining_roi and self.temp_roi_rect and event.button() == Qt.LeftButton:
            self.roi_rect = self.temp_roi_rect.normalized()
            self.temp_roi_rect = None
            self.roi_defined.emit(self.roi_rect)
            self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        if self.temp_roi_rect:
            painter.setPen(QPen(Qt.yellow, 2, Qt.DashLine))
            painter.drawRect(self.temp_roi_rect)
        elif self.roi_rect:
            painter.setPen(QPen(Qt.green, 2, Qt.SolidLine))
            painter.drawRect(self.roi_rect)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setGeometry(100, 100, 1600, 900)
        self.cameras = []
        self.video_frames = []
        self.selected_frame = None
        self.scanner_thread = None
        self.scanner = None
        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        left_panel = self.create_left_panel()
        main_content = self.create_main_content()
        main_layout.addWidget(left_panel)
        main_layout.addWidget(main_content, 1)
        self.setCentralWidget(main_widget)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frames)
        self.timer.start(40)
        self.load_cameras_from_config()

    def create_left_panel(self):
        left_panel = QWidget()
        left_panel.setFixedWidth(280)
        left_layout = QVBoxLayout(left_panel)
        self.camera_list = QListWidget()
        self.camera_list.itemClicked.connect(self.on_camera_list_select)
        add_button = QPushButton("Add Camera")
        add_button.clicked.connect(self.add_camera_dialog)
        self.edit_camera_button = QPushButton("Edit Camera")
        self.edit_camera_button.clicked.connect(self.edit_camera_dialog)
        remove_button = QPushButton("Remove Cam")
        remove_button.clicked.connect(self.remove_camera)
        btn_layout_1 = QHBoxLayout()
        btn_layout_1.addWidget(add_button)
        btn_layout_1.addWidget(remove_button)
        self.scan_button = QPushButton("Scan Network")
        self.scan_button.clicked.connect(self.scan_network)
        left_layout.addWidget(QLabel("Cameras"))
        left_layout.addWidget(self.camera_list)
        left_layout.addLayout(btn_layout_1)
        left_layout.addWidget(self.edit_camera_button)
        left_layout.addWidget(self.scan_button)
        self.motion_panel = self.create_motion_panel()
        left_layout.addWidget(self.motion_panel)
        left_layout.addStretch()
        return left_panel

    def create_motion_panel(self):
        # ... (Този метод остава същият)
        motion_panel = QFrame()
        motion_panel.setObjectName("motionPanel")
        motion_panel.setStyleSheet("#motionPanel { border-color: #555; }")
        layout = QFormLayout(motion_panel)
        layout.setContentsMargins(10, 10, 10, 10)
        title = QLabel("Motion Detection")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        self.motion_enabled_check = QCheckBox("Enable Motion Detection")
        self.motion_enabled_check.stateChanged.connect(self.update_motion_setting)
        self.sensitivity_slider = QSlider(Qt.Horizontal)
        self.sensitivity_slider.setRange(100, 10000)
        self.sensitivity_slider.setInvertedAppearance(True)
        self.sensitivity_slider.valueChanged.connect(self.update_motion_setting)
        self.post_motion_time_edit = QLineEdit()
        self.post_motion_time_edit.setFixedWidth(50)
        self.post_motion_time_edit.textChanged.connect(self.update_motion_setting)
        self.define_roi_button = QPushButton("Define ROI")
        self.define_roi_button.setCheckable(True)
        self.define_roi_button.toggled.connect(self.toggle_roi_definition)
        layout.addRow(title)
        layout.addRow(self.motion_enabled_check)
        layout.addRow("Sensitivity:", self.sensitivity_slider)
        layout.addRow("Post-Motion Record (s):", self.post_motion_time_edit)
        layout.addRow(self.define_roi_button)
        motion_panel.setEnabled(False)
        return motion_panel

    def create_main_content(self):
        # ... (Този метод остава същият)
        main_content = QWidget()
        main_content_layout = QVBoxLayout(main_content)
        self.tabs = QTabWidget()
        self.tabs.currentChanged.connect(self.on_tab_changed)
        live_view_widget = self.create_live_view_widget()
        recordings_widget = self.create_recordings_widget()
        self.tabs.addTab(live_view_widget, "Live View")
        self.tabs.addTab(recordings_widget, "Recordings")
        main_content_layout.addWidget(self.tabs)
        return main_content
        
    def create_live_view_widget(self):
        # ... (Този метод остава същият)
        live_view_widget = QWidget()
        live_view_layout = QVBoxLayout(live_view_widget)
        self.video_grid_widget = QWidget()
        self.video_grid_layout = QGridLayout(self.video_grid_widget)
        self.video_grid_layout.setSpacing(5)
        bottom_panel = self.create_bottom_panel()
        live_view_layout.addWidget(self.video_grid_widget, 1)
        live_view_layout.addWidget(bottom_panel)
        return live_view_widget

    def create_recordings_widget(self):
        # ... (Този метод остава същият)
        recordings_widget = QWidget()
        layout = QHBoxLayout(recordings_widget)
        splitter = QSplitter(Qt.Horizontal)
        self.fs_model = QFileSystemModel()
        self.fs_model.setRootPath(APP_DIR.as_posix())
        self.fs_model.setFilter(QDir.NoDotAndDotDot | QDir.AllDirs)
        self.dir_tree = QTreeView()
        self.dir_tree.setModel(self.fs_model)
        self.dir_tree.setRootIndex(self.fs_model.index(APP_DIR.as_posix()))
        for i in range(1, self.fs_model.columnCount()):
            self.dir_tree.hideColumn(i)
        self.dir_tree.setColumnWidth(0, 200)
        self.dir_tree.clicked.connect(self.on_dir_selected)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        self.file_list = QListWidget()
        recordings_controls = QHBoxLayout()
        play_button = QPushButton("Play / View")
        play_button.clicked.connect(self.play_selected_file)
        delete_button = QPushButton("Delete File")
        delete_button.clicked.connect(self.delete_selected_file)
        open_folder_button = QPushButton("Open Folder")
        open_folder_button.clicked.connect(self.open_selected_folder)
        recordings_controls.addWidget(play_button)
        recordings_controls.addWidget(delete_button)
        recordings_controls.addWidget(open_folder_button)
        right_layout.addWidget(self.file_list)
        right_layout.addLayout(recordings_controls)
        splitter.addWidget(self.dir_tree)
        splitter.addWidget(right_panel)
        splitter.setSizes([250, 750])
        layout.addWidget(splitter)
        return recordings_widget

    def create_bottom_panel(self):
        # ... (Този метод остава същият)
        panel = QFrame()
        panel.setMinimumHeight(180)
        panel.setMaximumHeight(180)
        panel_layout = QHBoxLayout(panel)
        toolbar = self.create_toolbar()
        log_panel = self.create_log_panel()
        panel_layout.addWidget(toolbar, 1)
        panel_layout.addWidget(log_panel, 1)
        return panel

    def create_toolbar(self):
        toolbar = QWidget()
        toolbar_layout = QVBoxLayout(toolbar)
        action_controls = QHBoxLayout()
        self.play_pause_btn = QPushButton("Pause")
        self.play_pause_btn.clicked.connect(self.toggle_stream)
        self.record_btn = QPushButton("Record")
        self.record_btn.clicked.connect(self.toggle_manual_recording)
        self.snapshot_btn = QPushButton("Snapshot")
        self.snapshot_btn.clicked.connect(self.take_snapshot)
        
        action_controls.addWidget(self.play_pause_btn)
        action_controls.addWidget(self.record_btn)
        action_controls.addWidget(self.snapshot_btn)
        
        ptz_grid = QGridLayout()
        # ... (PTZ бутоните остават същите)
        self.ptz_up = PTZButton("▲"); ptz_grid.addWidget(self.ptz_up, 0, 1)
        self.ptz_left = PTZButton("◀"); ptz_grid.addWidget(self.ptz_left, 1, 0)
        self.ptz_down = PTZButton("▼"); ptz_grid.addWidget(self.ptz_down, 1, 1)
        self.ptz_right = PTZButton("▶"); ptz_grid.addWidget(self.ptz_right, 1, 2)
        self.ptz_zoom_in = PTZButton("Zoom+"); ptz_grid.addWidget(self.ptz_zoom_in, 0, 3)
        self.ptz_zoom_out = PTZButton("Zoom-"); ptz_grid.addWidget(self.ptz_zoom_out, 1, 3)
        self.ptz_buttons = [self.ptz_up, self.ptz_down, self.ptz_left, self.ptz_right, self.ptz_zoom_in, self.ptz_zoom_out]
        self.ptz_up.pressed.connect(lambda: self.ptz_action(tilt=1.0))
        self.ptz_down.pressed.connect(lambda: self.ptz_action(tilt=-1.0))
        self.ptz_left.pressed.connect(lambda: self.ptz_action(pan=-1.0))
        self.ptz_right.pressed.connect(lambda: self.ptz_action(pan=1.0))
        self.ptz_zoom_in.pressed.connect(lambda: self.ptz_action(zoom=1.0))
        self.ptz_zoom_out.pressed.connect(lambda: self.ptz_action(zoom=-1.0))
        for btn in self.ptz_buttons: btn.released.connect(self.ptz_stop_action)
        
        ptz_speed_layout = QHBoxLayout()
        ptz_speed_layout.addWidget(QLabel("PTZ Speed:"))
        self.ptz_speed_slider = QSlider(Qt.Horizontal)
        self.ptz_speed_slider.setRange(1, 10)
        self.ptz_speed_slider.setValue(5)
        ptz_speed_layout.addWidget(self.ptz_speed_slider)
        toolbar_layout.addLayout(action_controls)
        toolbar_layout.addLayout(ptz_grid)
        toolbar_layout.addLayout(ptz_speed_layout)
        self.set_controls_enabled(False)
        return toolbar

    def create_log_panel(self):
        # ... (Този метод остава същият)
        log_panel = QWidget()
        log_layout = QVBoxLayout(log_panel)
        log_layout.addWidget(QLabel("Alerts & Actions"))
        self.log_list = QListWidget()
        self.log_list.setSelectionMode(QAbstractItemView.NoSelection)
        log_layout.addWidget(self.log_list)
        return log_panel
        
    def add_log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_list.insertItem(0, f"[{timestamp}] {message}")

    def add_camera_dialog(self):
        dialog = CameraDialog(parent=self)
        if dialog.exec_() == QDialog.Accepted: self.add_camera(dialog.get_data())

    def edit_camera_dialog(self):
        if not self.selected_frame:
            self.add_log("Please select a camera to edit.")
            return
        cam_obj = self.selected_frame.camera
        current_data = {"name": cam_obj.name, "url": cam_obj.rtsp_url, "user": cam_obj.user, "pass": cam_obj.password}
        dialog = CameraDialog(camera_data=current_data, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            self.update_camera(cam_obj, dialog.get_data())

    def add_camera(self, cam_data):
        # ... (Този метод остава същият)
        if not cam_data["name"] or not cam_data["url"]:
            self.add_log("Error: Name and URL cannot be empty.")
            return
        if any(cam.name == cam_data["name"] for cam in self.cameras):
            self.add_log(f"Error: Camera with name '{cam_data['name']}' already exists.")
            return
        try:
            new_hostname = urlparse(cam_data["url"]).hostname
            if new_hostname and any(urlparse(cam.rtsp_url).hostname == new_hostname for cam in self.cameras):
                self.add_log(f"Error: Camera with IP '{new_hostname}' already exists.")
                return
        except Exception as e:
            self.add_log(f"Could not validate URL: {e}")
            return
        cam = Camera(name=cam_data["name"], rtsp_url=cam_data["url"], user=cam_data.get("user"), password=cam_data.get("pass"), motion_config=cam_data.get("motion_config"))
        cam.log_message.connect(self.add_log)
        cam.motion_detected.connect(lambda: self.on_motion_status_changed(cam, True))
        cam.motion_stopped.connect(lambda: self.on_motion_status_changed(cam, False))
        if cam.start_stream():
            self.cameras.append(cam)
            self.camera_list.addItem(cam.name)
            self.add_log(f"Camera '{cam.name}' added successfully.")
            self.create_video_frame(cam)
            self.update_grid_layout()
            self.save_cameras_to_config()
        else:
            self.add_log(f"Error: Failed to connect to '{cam.name}'. Check URL.")
            cam.stop_stream()

    def update_camera(self, camera_to_update, new_data):
        # ... (Този метод остава същият)
        old_name = camera_to_update.name
        new_name = new_data["name"]
        if old_name != new_name and any(cam.name == new_name for cam in self.cameras):
            self.add_log(f"Error: Camera name '{new_name}' already exists.")
            return
        try:
            new_hostname = urlparse(new_data["url"]).hostname
            if new_hostname and any(urlparse(cam.rtsp_url).hostname == new_hostname and cam != camera_to_update for cam in self.cameras):
                self.add_log(f"Error: Camera with IP '{new_hostname}' already exists.")
                return
        except Exception as e:
            self.add_log(f"Could not validate new URL: {e}")
            return
        self.add_log(f"Updating camera '{old_name}'...")
        camera_to_update.stop_stream()
        camera_to_update.update_details(
            name=new_name, rtsp_url=new_data["url"],
            user=new_data["user"], password=new_data["pass"]
        )
        for i in range(self.camera_list.count()):
            item = self.camera_list.item(i)
            if item.text() == old_name:
                item.setText(new_name)
                break
        frame_widget = next((f for f in self.video_frames if f.camera == camera_to_update), None)
        if frame_widget: frame_widget.name_label.setText(new_name)
        self.add_log(f"Restarting stream for '{new_name}'...")
        camera_to_update.start_stream()
        self.save_cameras_to_config()
        self.add_log("Update complete.")

    def remove_camera(self):
        # ... (Този метод остава същият)
        current_item = self.camera_list.currentItem()
        if not current_item:
            self.add_log("No camera selected to remove.")
            return
        cam_name = current_item.text()
        cam_to_remove = next((c for c in self.cameras if c.name == cam_name), None)
        frame_to_remove = next((f for f in self.video_frames if f.camera.name == cam_name), None)
        if cam_to_remove:
            cam_to_remove.stop_stream()
            self.cameras.remove(cam_to_remove)
        if frame_to_remove:
            self.video_frames.remove(frame_to_remove)
            frame_to_remove.setParent(None)
            frame_to_remove.deleteLater()
        self.camera_list.takeItem(self.camera_list.row(current_item))
        self.add_log(f"Camera '{cam_name}' removed.")
        if self.selected_frame is frame_to_remove:
            self.selected_frame = None
            self.set_controls_enabled(False)
        self.update_grid_layout()
        self.save_cameras_to_config()

    def create_video_frame(self, camera):
        frame = VideoFrame(camera)
        frame.frame_clicked.connect(self.select_frame)
        frame.roi_defined.connect(self.set_camera_roi)
        self.video_frames.append(frame)
        if len(self.video_frames) == 1: self.select_frame(frame)

    def update_grid_layout(self):
        # ... (Този метод остава същият)
        for i in reversed(range(self.video_grid_layout.count())):
            widget = self.video_grid_layout.itemAt(i).widget()
            if widget: widget.setParent(None)
        num_frames = len(self.video_frames)
        cols = 1 if num_frames <= 1 else (2 if num_frames <= 4 else 3)
        for i, frame in enumerate(self.video_frames):
            row, col = i // cols, i % cols
            self.video_grid_layout.addWidget(frame, row, col)

    def select_frame(self, frame_to_select):
        if self.selected_frame: self.selected_frame.set_selected(False)
        self.selected_frame = frame_to_select
        self.selected_frame.set_selected(True)
        self.edit_camera_button.setEnabled(True)
        self.motion_panel.setEnabled(True)
        self.load_motion_settings_for_camera(frame_to_select.camera)
        for i in range(self.camera_list.count()):
            item = self.camera_list.item(i)
            if item.text() == self.selected_frame.camera.name:
                self.camera_list.setCurrentRow(i)
                break
        self.add_log(f"Selected camera: '{self.selected_frame.camera.name}'")
        self.update_control_states()

    def on_camera_list_select(self, item):
        camera_name = item.text()
        for frame in self.video_frames:
            if frame.camera.name == camera_name:
                self.select_frame(frame)
                break

    def set_controls_enabled(self, enabled, ptz_enabled=False):
        self.play_pause_btn.setEnabled(enabled)
        self.record_btn.setEnabled(enabled)
        self.snapshot_btn.setEnabled(enabled)
        self.ptz_speed_slider.setEnabled(ptz_enabled)
        for btn in self.ptz_buttons: btn.setEnabled(ptz_enabled)

    def update_control_states(self):
        if not self.selected_frame:
            self.set_controls_enabled(False)
            self.edit_camera_button.setEnabled(False)
            self.motion_panel.setEnabled(False)
            return
        cam = self.selected_frame.camera
        is_ptz_ready = ONVIF_ENABLED and cam.ptz_service is not None
        self.set_controls_enabled(True, ptz_enabled=is_ptz_ready)
        if cam.is_running: self.play_pause_btn.setText("Pause")
        else:
            self.play_pause_btn.setText("Play")
            self.record_btn.setEnabled(False)
            self.snapshot_btn.setEnabled(False)
        if cam.is_manual_recording:
            self.record_btn.setText("Stop")
            self.record_btn.setStyleSheet(f"background-color: {RECORDING_COLOR};")
        else:
            self.record_btn.setText("Record")
            self.record_btn.setStyleSheet("")
        
    def update_frames(self):
        # ... (Този метод остава същият)
        for frame_widget in self.video_frames:
            camera = frame_widget.camera
            if camera.is_running:
                frame = camera.get_frame()
                if frame is not None:
                    h, w, ch = frame.shape
                    bytes_per_line = ch * w
                    qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format_BGR888)
                    pixmap = QPixmap.fromImage(qt_image)
                    frame_widget.video_label.setPixmap(pixmap)
                else: frame_widget.video_label.setText(f"No Signal\n({camera.name})")
            else: frame_widget.video_label.setText(f"Stream Paused\n({camera.name})")
    
    def toggle_stream(self):
        # ... (Този метод остава същият)
        if not self.selected_frame: return
        cam = self.selected_frame.camera
        if cam.is_running: cam.stop_stream()
        else: cam.start_stream()
        self.add_log(f"Stream {'paused' if not cam.is_running else 'started'} for '{cam.name}'.")
        self.update_control_states()

    def toggle_manual_recording(self):
        if not self.selected_frame: return
        cam = self.selected_frame.camera
        if not cam.is_manual_recording:
            if cam.start_recording():
                cam.is_manual_recording = True
        else:
            cam.is_manual_recording = False
            if not cam.is_motion_recording:
                cam.stop_recording()
        self.update_control_states()

    def take_snapshot(self):
        # ... (Този метод остава същият)
        if not self.selected_frame: return
        cam = self.selected_frame.camera
        filename = cam.take_snapshot()
        if filename: self.add_log(f"Snapshot saved: {filename.name}")
        else: self.add_log(f"Error: Could not take snapshot for '{cam.name}'.")

    def ptz_action(self, pan=0.0, tilt=0.0, zoom=0.0):
        # ... (Този метод остава същият)
        if self.selected_frame and self.selected_frame.camera:
            speed = self.ptz_speed_slider.value() / 10.0
            if pan != 0.0: pan *= speed
            if tilt != 0.0: tilt *= speed
            if zoom != 0.0: zoom *= speed
            self.selected_frame.camera.ptz_move(pan, tilt, zoom)

    def ptz_stop_action(self):
        # ... (Този метод остава същият)
        if self.selected_frame and self.selected_frame.camera:
            self.selected_frame.camera.ptz_stop()

    def save_cameras_to_config(self):
        # ... (Този метод остава същият)
        config_data = []
        for cam in self.cameras:
            config_data.append({
                "name": cam.name, "url": cam.rtsp_url, 
                "user": cam.user, "pass": cam.password,
                "motion_config": cam.get_motion_config()
            })
        with open(CONFIG_FILE, 'w') as f: json.dump(config_data, f, indent=4)
        self.add_log("Camera list saved.")

    def load_cameras_from_config(self):
        if not CONFIG_FILE.exists(): return
        try:
            with open(CONFIG_FILE, 'r') as f: config_data = json.load(f)
            for cam_data in config_data: self.add_camera(cam_data)
        except Exception as e: self.add_log(f"Error loading config: {e}")

    def get_local_subnet(self):
        # ... (Този метод остава същият)
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
            return IPv4Network(f"{ip}/24", strict=False)
        except Exception as e:
            self.add_log(f"Error detecting subnet: {e}")
            return None

    def scan_network(self):
        # ... (Този метод остава същият)
        subnet = self.get_local_subnet()
        if not subnet: return
        self.progress_dialog = QProgressDialog("Scanning your network for cameras...", "Cancel", 0, 100, self)
        self.progress_dialog.setWindowTitle("Scanning Network")
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.scanner_thread = QThread()
        self.scanner = NetworkScanner(subnet)
        self.scanner.moveToThread(self.scanner_thread)
        self.progress_dialog.canceled.connect(self.scanner.cancel)
        self.scanner.scan_progress.connect(self.progress_dialog.setValue)
        self.scanner.camera_found.connect(self.add_scanned_camera)
        self.scanner.scan_finished.connect(self.on_scan_finished)
        self.scanner_thread.started.connect(self.scanner.run)
        self.scan_button.setEnabled(False)
        self.scanner_thread.start()
        self.progress_dialog.show()

    def add_scanned_camera(self, ip):
        # ... (Този метод остава същият)
        self.add_log(f"Potential camera found at {ip}.")
        if any(urlparse(cam.rtsp_url).hostname == ip for cam in self.cameras):
            self.add_log(f"Camera with IP {ip} already exists. Skipping.")
            return
        cam_data = { "name": f"Cam @ {ip}", "url": f"rtsp://{ip}:554/", "user": "", "pass": "" }
        self.add_camera(cam_data)

    def on_scan_finished(self, message):
        # ... (Този метод остава същият)
        self.add_log(message)
        self.progress_dialog.close()
        self.scan_button.setEnabled(True)
        if self.scanner_thread:
            self.scanner_thread.quit()
            self.scanner_thread.wait()

    def on_tab_changed(self, index):
        if self.tabs.tabText(index) == "Recordings": self.refresh_recordings_view()

    def refresh_recordings_view(self):
        current_index = self.dir_tree.currentIndex()
        if current_index.isValid(): self.on_dir_selected(current_index)
        else: self.file_list.clear()

    def on_dir_selected(self, index):
        self.file_list.clear()
        path = self.fs_model.filePath(index)
        try:
            files = sorted(os.listdir(path), reverse=True)
            for item in files:
                if item.endswith(('.mp4', '.jpg', '.png')):
                    self.file_list.addItem(item)
        except Exception as e:
            self.add_log(f"Could not read directory: {e}")

    def get_selected_file_path(self):
        # ... (Този метод остава същият)
        dir_index = self.dir_tree.currentIndex()
        if not dir_index.isValid():
            self.add_log("Please select a camera folder first.")
            return None, None
        selected_file_item = self.file_list.currentItem()
        if not selected_file_item:
            self.add_log("Please select a file from the list.")
            return None, None
        dir_path = self.fs_model.filePath(dir_index)
        file_path = Path(dir_path) / selected_file_item.text()
        return file_path, selected_file_item

    def play_selected_file(self):
        # ... (Този метод остава същият)
        file_path, _ = self.get_selected_file_path()
        if not file_path: return
        if sys.platform == "win32": os.startfile(file_path)
        elif sys.platform == "darwin": subprocess.Popen(["open", file_path])
        else: subprocess.Popen(["xdg-open", file_path])

    def delete_selected_file(self):
        # ... (Този метод остава същият)
        file_path, item = self.get_selected_file_path()
        if not file_path: return
        reply = QMessageBox.question(self, 'Confirm Deletion', 
                                     f"Are you sure you want to permanently delete\n{file_path.name}?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                os.remove(file_path)
                self.file_list.takeItem(self.file_list.row(item))
                self.add_log(f"Deleted file: {file_path.name}")
            except Exception as e:
                self.add_log(f"Error deleting file: {e}")

    def open_selected_folder(self):
        # ... (Този метод остава същият)
        dir_index = self.dir_tree.currentIndex()
        if not dir_index.isValid():
            self.add_log("Please select a camera folder first.")
            return
        dir_path = self.fs_model.filePath(dir_index)
        if not os.path.isdir(dir_path):
            dir_path = os.path.dirname(dir_path)
        self.add_log(f"Opening folder: {dir_path}")
        if sys.platform == "win32": os.startfile(dir_path)
        elif sys.platform == "darwin": subprocess.Popen(['open', dir_path])
        else: subprocess.Popen(['xdg-open', dir_path])

    def load_motion_settings_for_camera(self, camera):
        self.motion_enabled_check.setChecked(camera.motion_enabled)
        self.sensitivity_slider.setValue(camera.motion_sensitivity)
        self.post_motion_time_edit.setText(str(camera.post_motion_record_time))
        frame_widget = next((f for f in self.video_frames if f.camera == camera), None)
        if frame_widget:
            if camera.roi:
                x, y, w, h = camera.roi
                frame_widget.roi_rect = QRect(x, y, w, h)
            else:
                frame_widget.roi_rect = None
            frame_widget.update()

    def update_motion_setting(self):
        if not self.selected_frame: return
        cam = self.selected_frame.camera
        cam.motion_enabled = self.motion_enabled_check.isChecked()
        cam.motion_sensitivity = self.sensitivity_slider.value()
        try:
            cam.post_motion_record_time = int(self.post_motion_time_edit.text())
        except ValueError:
            pass
        self.save_cameras_to_config()

    def toggle_roi_definition(self, checked):
        if not self.selected_frame:
            self.define_roi_button.setChecked(False)
            return
        self.selected_frame.is_defining_roi = checked
        if checked:
            self.add_log("Draw a rectangle on the selected camera to define the Region of Interest.")
            self.define_roi_button.setText("Finish ROI")
        else:
            self.add_log("ROI definition finished.")
            self.define_roi_button.setText("Define ROI")
            if self.selected_frame.roi_rect is None:
                self.set_camera_roi(QRect())

    def set_camera_roi(self, rect):
        if not self.selected_frame: return
        cam = self.selected_frame.camera
        if rect.isNull() or rect.isEmpty():
            cam.roi = None
            self.add_log(f"ROI for '{cam.name}' has been cleared.")
        else:
            cam.roi = (rect.x(), rect.y(), rect.width(), rect.height())
            self.add_log(f"ROI for '{cam.name}' set to {cam.roi}")
        self.selected_frame.is_defining_roi = False
        self.define_roi_button.setChecked(False)
        self.save_cameras_to_config()

    def on_motion_status_changed(self, camera, is_motion):
        frame_widget = next((f for f in self.video_frames if f.camera == camera), None)
        if frame_widget:
            frame_widget.set_selected(frame_widget.is_selected)

    def closeEvent(self, event):
        self.save_cameras_to_config()
        print("Closing application, stopping all streams...")
        for cam in self.cameras: cam.stop_stream()
        if self.scanner: self.scanner.cancel()
        if self.scanner_thread:
            self.scanner_thread.quit()
            self.scanner_thread.wait()
        event.accept()


if __name__ == "__main__":
    if not ONVIF_ENABLED:
        print("WARNING: 'onvif-zeep' library not found. PTZ functionality will be disabled.")
        print("Please install it using: pip install onvif-zeep")
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
