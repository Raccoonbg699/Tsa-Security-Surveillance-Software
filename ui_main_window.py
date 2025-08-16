import uuid
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime
import cv2
import numpy as np
from queue import Empty
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QStackedWidget, QLabel, QMessageBox, QProgressDialog, QListWidgetItem, QFormLayout,
    QFileDialog
)
from PySide6.QtCore import QSize, Qt, QThread, QTimer, Signal, QTime
from PySide6.QtGui import QIcon

from data_manager import DataManager, get_translator
from ui_pages import CamerasPage, LiveViewPage, RecordingsPage, SettingsPage, UsersPage
from ui_dialogs import CameraDialog, UserDialog
from video_worker import VideoWorker, RecordingWorker
from ui_widgets import VideoFrame
from network_scanner import NetworkScanner, get_local_subnet
from ui_media_viewer import MediaViewerDialog
from ui_info_dialog import InfoDialog
from ui_remote_dialogs import RemoteSystemsPage
from remote_client import RemoteClient

class MainWindow(QMainWindow):
    logout_requested = Signal()
    restart_requested = Signal()

    def __init__(self, base_dir, user_role, command_queue):
        super().__init__()
        self.translator = get_translator()
        self.base_dir = base_dir
        self.user_role = user_role
        self.command_queue = command_queue
        
        self.setWindowTitle(self.translator.get_string("main_window_title"))
        self.setGeometry(100, 100, 1280, 720)

        self.video_workers = {}
        self.active_video_widgets = {}
        self.recording_worker = None
        self.created_pages = {}
        
        self.latest_grid_frames = {}
        self.grid_recording_timer = QTimer(self)
        self.grid_recording_timer.timeout.connect(self._compose_and_record_grid_frame)
        self.is_grid_recording = False
        
        self.scanner_thread = None
        self.scanner = None
        self.progress_dialog = None
        
        self.remote_client = None
        self.is_remote_mode = False

        self.command_timer = QTimer(self)
        self.command_timer.timeout.connect(self.process_command_queue)
        self.command_timer.start(250)
        
        # --- SCHEDULE LOGIC ---
        self.scheduled_recorders = {}
        self.schedule_check_timer = QTimer(self)
        self.schedule_check_timer.timeout.connect(self.check_schedules)
        self.schedule_check_timer.start(30000)

        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setCentralWidget(main_widget)

        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(200)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(10, 10, 10, 10)
        sidebar_layout.setSpacing(10)

        self.pages = QStackedWidget()
        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.pages)
        
        btn_live_view = self.create_nav_button(self.translator.get_string("live_view"), "icons/video-camera.png")
        btn_cameras = self.create_nav_button(self.translator.get_string("cameras"), "icons/camera.png")
        btn_recordings = self.create_nav_button(self.translator.get_string("recordings"), "icons/archive.png")
        self.btn_users = self.create_nav_button(self.translator.get_string("users"), "icons/user.png")
        btn_settings = self.create_nav_button(self.translator.get_string("settings"), "icons/gear.png")
        
        self.btn_remote = self.create_nav_button("Отдалечени системи", "icons/remote.png")
        self.btn_disconnect = self.create_nav_button("Прекъсни връзката", "icons/disconnect.png")
        self.btn_disconnect.hide()
        
        btn_logout = self.create_nav_button(self.translator.get_string("logout"), "icons/logout.png")

        sidebar_layout.addWidget(btn_live_view)
        sidebar_layout.addWidget(btn_cameras)
        sidebar_layout.addWidget(btn_recordings)
        sidebar_layout.addStretch()
        sidebar_layout.addWidget(self.btn_users)
        sidebar_layout.addWidget(btn_settings)
        sidebar_layout.addWidget(self.btn_remote)
        sidebar_layout.addWidget(self.btn_disconnect)
        sidebar_layout.addWidget(btn_logout)

        btn_live_view.clicked.connect(self.show_live_view_page)
        btn_cameras.clicked.connect(self.show_cameras_page)
        btn_recordings.clicked.connect(self.show_recordings_page)
        self.btn_users.clicked.connect(self.show_users_page)
        btn_settings.clicked.connect(self.show_settings_page)
        self.btn_remote.clicked.connect(self.show_remote_systems_dialog)
        self.btn_disconnect.clicked.connect(self.disconnect_from_remote)
        btn_logout.clicked.connect(self.logout_requested.emit)
        
        self.apply_role_permissions()
        
        btn_live_view.setChecked(True)
        self.show_live_view_page()
    
    def process_command_queue(self):
        try:
            command = self.command_queue.get_nowait()
            action = command.get("action")
            payload = command.get("payload")
            
            print(f"Received command: {action} with payload: {payload}")

            if action == "snapshot":
                self.take_snapshot(remote_camera_id=payload.get("camera_id"))
            elif action == "toggle_record":
                 self.toggle_manual_recording(payload.get("state"), remote_camera_id=payload.get("camera_id"))
            elif action == "delete_event":
                self.delete_event(remote_event_id=payload.get("event_id"))

        except Empty:
            pass
        except Exception as e:
            print(f"Error processing command: {e}")

    def create_nav_button(self, text, relative_icon_path):
        button = QPushButton(text)
        button.setObjectName("NavButton")
        if "logout" not in relative_icon_path and "remote" not in relative_icon_path and "disconnect" not in relative_icon_path:
            button.setCheckable(True)
            button.setAutoExclusive(True)
        
        full_icon_path = self.base_dir / relative_icon_path
        if full_icon_path.exists():
            button.setIcon(QIcon(str(full_icon_path)))
        else:
            print(f"Предупреждение: Иконата не е намерена: {full_icon_path}")
        button.setIconSize(QSize(24, 24))
        return button
    
    def apply_role_permissions(self):
        is_admin = self.user_role == "Administrator"
        self.btn_users.setVisible(is_admin)

    def switch_to_page(self, page_name):
        current_widget = self.pages.currentWidget()
        if hasattr(current_widget, 'page_name') and current_widget.page_name == "live_view":
             self.stop_all_streams()

        if page_name not in self.created_pages:
            page = None
            if page_name == "live_view":
                page = LiveViewPage()
                page.page_name = page_name
                page.snapshot_button.clicked.connect(self.take_snapshot)
                page.record_button.toggled.connect(self.toggle_manual_recording)
                page.grid_1x1_button.clicked.connect(self.update_grid_layout)
                page.grid_2x2_button.clicked.connect(self.update_grid_layout)
                page.grid_3x3_button.clicked.connect(self.update_grid_layout)
                page.camera_selector.currentIndexChanged.connect(self.update_grid_layout)
            elif page_name == "cameras":
                page = CamerasPage()
                page.page_name = page_name
                page.add_button.clicked.connect(self.add_camera)
                page.edit_button.clicked.connect(self.edit_camera)
                page.delete_button.clicked.connect(self.delete_camera)
                page.scan_button.clicked.connect(self.scan_network)
                page.search_input.textChanged.connect(self.filter_cameras_list)
            elif page_name == "recordings":
                page = RecordingsPage()
                page.page_name = page_name
            elif page_name == "settings":
                page = SettingsPage()
                page.page_name = page_name
                page.save_button.clicked.connect(self.save_settings)
            elif page_name == "users":
                page = UsersPage()
                page.page_name = page_name
                page.add_button.clicked.connect(self.add_user)
                page.edit_button.clicked.connect(self.edit_user)
                page.delete_button.clicked.connect(self.delete_user)

            if page:
                self.created_pages[page_name] = page
                self.pages.addWidget(page)
        
        self.pages.setCurrentWidget(self.created_pages[page_name])
        
        if page_name == "live_view":
            self.start_all_streams()
        elif page_name == "recordings":
            self.setup_recordings_page()
            self.refresh_recordings_view()
        elif page_name == "cameras":
            self.refresh_cameras_view()
        elif page_name == "settings":
            self.load_settings()
        elif page_name == "users":
            self.refresh_users_view()

    def filter_cameras_list(self):
        page = self.created_pages.get("cameras")
        if not page: return
        search_text = page.search_input.text().lower()
        for i in range(page.list_widget.count()):
            item = page.list_widget.item(i)
            item_text = item.text().lower()
            if search_text in item_text:
                item.setHidden(False)
            else:
                item.setHidden(True)

    def show_live_view_page(self): self.switch_to_page("live_view")
    def show_cameras_page(self): self.switch_to_page("cameras")
    def show_recordings_page(self): self.switch_to_page("recordings")
    
    def show_settings_page(self):
        self.switch_to_page("settings")
        page = self.created_pages.get("settings")
        if not page: return
        is_admin_local = (self.user_role == "Administrator" and not self.is_remote_mode)
        page.path_edit.setVisible(is_admin_local)
        page.browse_button.setVisible(is_admin_local)
        page.recording_structure_combo.setVisible(is_admin_local)
        page.save_button.setVisible(is_admin_local)
        form_layout = page.layout().itemAt(1)
        for i in range(form_layout.rowCount()):
            label_item = form_layout.itemAt(i, QFormLayout.ItemRole.LabelRole)
            if label_item:
                label_widget = label_item.widget()
                if label_widget.text() in [self.translator.get_string("recordings_folder_label"), self.translator.get_string("recording_structure_label")]:
                    label_widget.setVisible(is_admin_local)

    def show_users_page(self):
        if self.user_role == "Administrator" and not self.is_remote_mode:
            self.switch_to_page("users")

    def setup_recordings_page(self):
        page = self.created_pages.get("recordings")
        if not page or hasattr(page, 'is_setup'): return
        
        page.view_in_app_button.clicked.connect(self.view_event_in_app)
        page.open_in_player_button.clicked.connect(self.view_event_in_player)
        page.open_folder_button.clicked.connect(self.open_event_folder)
        page.info_button.clicked.connect(self.show_event_info)
        page.delete_button.clicked.connect(self.delete_event)
        
        page.camera_filter.currentIndexChanged.connect(self.apply_event_filters)
        page.event_type_filter.currentIndexChanged.connect(self.apply_event_filters)
        
        if self.user_role == "Administrator":
            page.delete_button.show()
        else:
            page.delete_button.hide()

        page.is_setup = True
        
    def scan_network(self):
        subnet = get_local_subnet()
        if not subnet:
            QMessageBox.warning(self, "Грешка", "Не може да се определи локалната мрежа.")
            return
        self.progress_dialog = QProgressDialog("Сканиране на мрежата за камери...", "Отказ", 0, 100, self)
        self.progress_dialog.setWindowTitle("Сканиране")
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.scanner_thread = QThread()
        self.scanner = NetworkScanner(subnet)
        self.scanner.moveToThread(self.scanner_thread)
        self.scanner.scan_progress.connect(self.progress_dialog.setValue)
        self.scanner.camera_found.connect(self.add_scanned_camera)
        self.scanner.scan_finished.connect(self.on_scan_finished)
        self.progress_dialog.canceled.connect(self.scanner.cancel)
        self.scanner_thread.started.connect(self.scanner.run)
        page = self.created_pages.get("cameras")
        if page: page.scan_button.setEnabled(False)
        self.scanner_thread.start()
        self.progress_dialog.show()

    def add_scanned_camera(self, ip_address):
        cameras = DataManager.load_cameras()
        if any(ip_address in cam.get('rtsp_url', '') for cam in cameras):
            print(f"Камера с IP {ip_address} вече съществува. Пропускане.")
            return
        new_cam_data = { "id": str(uuid.uuid4()), "name": f"Камера @ {ip_address}", "rtsp_url": f"rtsp://{ip_address}:554/", "is_active": True, "motion_enabled": True }
        cameras.append(new_cam_data)
        DataManager.save_cameras(cameras)
        self.refresh_cameras_view()

    def on_scan_finished(self, message):
        QMessageBox.information(self, "Сканирането приключи", message)
        self.progress_dialog.close()
        page = self.created_pages.get("cameras")
        if page: page.scan_button.setEnabled(True)
        if self.scanner_thread:
            self.scanner_thread.quit()
            self.scanner_thread.wait()
            self.scanner_thread = None
            self.scanner = None
            
    def load_settings(self):
        page = self.created_pages.get("settings")
        if not page: return
        settings_data = DataManager.load_settings()
        page.theme_combo.setCurrentText(self.translator.get_string("dark_theme") if settings_data.get("theme") == "dark" else self.translator.get_string("light_theme"))
        page.grid_combo.setCurrentText(settings_data.get("default_grid", "2x2"))
        page.path_edit.setText(settings_data.get("recording_path", ""))
        lang_code = settings_data.get("language", "bg")
        index = page.lang_combo.findData(lang_code)
        if index != -1: page.lang_combo.setCurrentIndex(index)
        structure_mode = settings_data.get("recording_structure", "single")
        index = page.recording_structure_combo.findData(structure_mode)
        if index != -1: page.recording_structure_combo.setCurrentIndex(index)

    def apply_theme(self, theme_name):
        style_file_name = "style.qss" if theme_name == "dark" else "style_light.qss"
        style_file = self.base_dir / style_file_name
        try:
            with open(style_file, "r", encoding="utf-8") as f:
                style_sheet = f.read()
                QApplication.instance().setStyleSheet(style_sheet)
        except FileNotFoundError:
            print(f"Предупреждение: Файлът със стилове {style_file} не е намерен.")

    def save_settings(self):
        page = self.created_pages.get("settings")
        if not page: return
        current_settings = DataManager.load_settings()
        old_lang = current_settings.get("language")
        new_theme = "dark" if page.theme_combo.currentText() == self.translator.get_string("dark_theme") else "light"
        new_lang = page.lang_combo.currentData()
        new_structure = page.recording_structure_combo.currentData()
        new_settings = {
            "theme": new_theme,
            "default_grid": page.grid_combo.currentText(),
            "recording_path": page.path_edit.text(),
            "language": new_lang,
            "recording_structure": new_structure
        }
        DataManager.save_settings(new_settings)
        self.apply_theme(new_theme)
        if old_lang != new_lang: self.restart_requested.emit()
        else: QMessageBox.information(self, "Успех", "Настройките бяха запазени успешно!")
        
    def start_all_streams(self):
        self.stop_all_streams()

        page = self.created_pages.get("live_view")
        if not page: return
        page.camera_selector.clear()

        cameras_data = self.load_cameras()
        if cameras_data is None:
            print("Неуспешно зареждане на камери.")
            return

        active_cameras = [cam for cam in cameras_data if cam.get("is_active")]
        
        for cam_data in active_cameras:
            cam_id = cam_data.get("id")
            page.camera_selector.addItem(cam_data["name"], cam_id)
            
            frame_widget = VideoFrame(camera_name=cam_data.get("name"), camera_id=cam_id)
            frame_widget.double_clicked.connect(self.toggle_fullscreen_camera)
            
            self.active_video_widgets[cam_id] = frame_widget
            
            self.start_single_worker(cam_data, frame_widget)

        self.update_grid_layout()

    def start_single_worker(self, cam_data, frame_widget):
        cam_id = cam_data.get("id")
        worker = VideoWorker(camera_data=cam_data, recording_path=None)
        worker.ImageUpdate.connect(frame_widget.update_frame)
        worker.StreamStatus.connect(frame_widget.update_status)
        worker.MotionDetected.connect(self.on_motion_detected)
        worker.finished.connect(lambda cid=cam_id: self.handle_worker_finished(cid))
        worker.start()
        self.video_workers[cam_id] = worker
    
    def check_schedules(self):
        """Проверява графиците и стартира/спира записи."""
        if self.is_remote_mode: return

        now = datetime.now()
        weekday = now.weekday()
        days_bg = ["Понеделник", "Вторник", "Сряда", "Четвъртък", "Петък", "Събота", "Неделя"]
        current_day_name_bg = days_bg[weekday]
        current_time = QTime.currentTime()

        all_cameras = self.load_cameras()
        if not all_cameras: return
        
        for cam_data in all_cameras:
            cam_id = cam_data.get("id")
            schedule = cam_data.get("schedule", {})
            day_schedule = schedule.get(current_day_name_bg)

            should_record = False
            if day_schedule and day_schedule.get("enabled"):
                start_time = QTime.fromString(day_schedule["start"], "HH:mm")
                end_time = QTime.fromString(day_schedule["end"], "HH:mm")
                if start_time <= current_time < end_time:
                    should_record = True
            
            is_currently_recording = cam_id in self.scheduled_recorders
            worker = self.video_workers.get(cam_id)
            widget = self.active_video_widgets.get(cam_id)
            if not worker or not widget: continue

            if should_record and not is_currently_recording:
                # Стартираме запис
                recording_path = self.get_recording_path_for_camera(worker)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_name = self.sanitize_filename(worker.camera_data['name'])
                filename = recording_path / f"sched_{safe_name}_{timestamp}.mp4"
                
                frame = worker.get_latest_frame()
                if frame is None: continue
                height, width, _ = frame.shape
                
                recorder = RecordingWorker(str(filename), width, height, 20.0)
                worker.FrameForRecording.connect(recorder.add_frame)
                recorder.start()
                self.scheduled_recorders[cam_id] = recorder
                widget.set_recording_state(True)
                self.add_event(cam_id, "Запис по график", str(filename))
                print(f"Запис по график стартиран за {cam_id}")

            elif not should_record and is_currently_recording:
                # Спираме запис
                recorder = self.scheduled_recorders.pop(cam_id, None)
                if recorder:
                    try: worker.FrameForRecording.disconnect(recorder.add_frame)
                    except (TypeError, RuntimeError): pass
                    recorder.stop()
                    recorder.wait()
                    widget.set_recording_state(False)
                    print(f"Запис по график спрян за {cam_id}")


    def handle_worker_finished(self, cam_id):
        print(f"Нишката за камера {cam_id} приключи. Рестартиране след 5 секунди...")
        if cam_id in self.video_workers:
            self.video_workers.pop(cam_id, None)
            cameras_data = self.load_cameras()
            if cameras_data is None: return
            cam_data = next((c for c in cameras_data if c.get("id") == cam_id), None)
            frame_widget = self.active_video_widgets.get(cam_id)
            if cam_data and frame_widget:
                QTimer.singleShot(5000, lambda: self.start_single_worker(cam_data, frame_widget))

    def stop_all_streams(self):
        if self.is_grid_recording: self.stop_grid_recording()
        if self.recording_worker:
            worker, _ = self.get_camera_to_control()
            if worker:
                try: worker.FrameForRecording.disconnect(self.handle_single_frame_for_recording)
                except (TypeError, RuntimeError): pass
            self.recording_worker.stop()
            self.recording_worker.wait()
            self.recording_worker = None
        
        for worker in self.video_workers.values():
            worker.stop()
            worker.wait()
        self.video_workers.clear()
        
        page = self.created_pages.get("live_view")
        if page:
            while page.grid_layout.count():
                child = page.grid_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
        
        self.active_video_widgets.clear()
    
    def load_cameras(self):
        """Зарежда камерите или от локален файл, или от отдалечена система."""
        if self.is_remote_mode and self.remote_client:
            cameras = self.remote_client.get_cameras()
            if cameras is None:
                QMessageBox.critical(self, "Грешка", "Неуспешно зареждане на камери от отдалечена система.")
                self.disconnect_from_remote()
                return None
            return cameras
        else:
            return DataManager.load_cameras()

    def load_events(self):
        """Зарежда записите или от локален файл, или от отдалечена система."""
        if self.is_remote_mode and self.remote_client:
            events = self.remote_client.get_recordings()
            if events is None:
                QMessageBox.critical(self, "Грешка", "Неуспешно зареждане на записи от отдалечена система.")
                self.disconnect_from_remote()
                return None
            return events
        else:
            return DataManager.load_events()

    def refresh_cameras_view(self):
        page = self.created_pages.get("cameras")
        if not page: return
        page.list_widget.clear()
        
        cameras_data = self.load_cameras()
        if cameras_data is None: return

        for cam in cameras_data:
            status = self.translator.get_string("camera_status_active") if cam.get('is_active') else self.translator.get_string("camera_status_inactive")
            motion = self.translator.get_string("motion_detection_on") if cam.get('motion_enabled') else self.translator.get_string("motion_detection_off")
            item_text = f"{cam['name']} - {status} - {motion}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, cam)
            page.list_widget.addItem(item)
            
        is_admin_local = (self.user_role == "Administrator" and not self.is_remote_mode)
        page.add_button.setVisible(is_admin_local)
        page.edit_button.setVisible(is_admin_local)
        page.delete_button.setVisible(is_admin_local)
        page.scan_button.setVisible(is_admin_local)
    
    def refresh_recordings_view(self):
        page = self.created_pages.get("recordings")
        if not page: return
        
        if self.is_remote_mode:
            page.view_in_app_button.setText("Преглед (Изтегляне)")
            page.open_in_player_button.hide()
            page.open_folder_button.hide()
            page.info_button.hide()
        else:
            page.view_in_app_button.setText("Преглед в програмата")
            page.open_in_player_button.show()
            page.open_folder_button.show()
            page.info_button.show()
            
        all_events = self.load_events()
        if all_events is None: return
            
        cameras = sorted(list(set(event.get("camera_name") for event in all_events)))
        event_types = sorted(list(set(event.get("event_type") for event in all_events)))
        page.camera_filter.blockSignals(True)
        page.event_type_filter.blockSignals(True)
        page.camera_filter.clear()
        page.event_type_filter.clear()
        page.camera_filter.addItem(self.translator.get_string("all_cameras_filter"))
        page.event_type_filter.addItem(self.translator.get_string("all_types_filter"))
        page.camera_filter.addItems(cameras)
        page.event_type_filter.addItems(event_types)
        page.camera_filter.blockSignals(False)
        page.event_type_filter.blockSignals(False)
        self.apply_event_filters()

    def apply_event_filters(self):
        page = self.created_pages.get("recordings")
        if not page: return
        cam_filter = page.camera_filter.currentText()
        type_filter = page.event_type_filter.currentText()
        if cam_filter == self.translator.get_string("all_cameras_filter"): cam_filter = ""
        if type_filter == self.translator.get_string("all_types_filter"): type_filter = ""
        page.list_widget.clear()

        all_events = self.load_events()
        if all_events is None: return

        for event in all_events:
            cam_match = cam_filter == "" or cam_filter == event.get("camera_name")
            type_match = type_filter == "" or type_filter == event.get("event_type")
            if cam_match and type_match:
                item_text = f"{event['timestamp']} - {event['camera_name']} ({event['event_type']})"
                item = QListWidgetItem(item_text)
                item.setData(Qt.ItemDataRole.UserRole, event)
                page.list_widget.addItem(item)
    
    def view_event_in_app(self):
        page = self.created_pages.get("recordings")
        if not page: return
        selected_items = page.list_widget.selectedItems()
        if not selected_items: return
        
        event_data = selected_items[0].data(Qt.ItemDataRole.UserRole)
        remote_file_path = event_data.get("file_path")

        if self.is_remote_mode:
            download_dir = Path.home() / "TSA-Security Downloads"
            download_dir.mkdir(exist_ok=True)
            local_file_path = download_dir / Path(remote_file_path).name
            
            success = self.remote_client.download_file(remote_file_path, str(local_file_path))
            if success:
                print(f"Файлът е изтеглен: {local_file_path}")
                viewer = MediaViewerDialog(str(local_file_path), parent=self)
                viewer.exec()
            else:
                QMessageBox.critical(self, "Грешка", "Неуспешно изтегляне на файла.")
            return

        if not remote_file_path or not os.path.exists(remote_file_path):
            QMessageBox.warning(self, "Грешка", f"Файлът не е намерен:\n{remote_file_path}")
            return
        
        viewer = MediaViewerDialog(remote_file_path, parent=self)
        viewer.exec()

    def view_event_in_player(self):
        page = self.created_pages.get("recordings")
        if not page: return
        selected_items = page.list_widget.selectedItems()
        if not selected_items: return
        
        event_data = selected_items[0].data(Qt.ItemDataRole.UserRole)
        file_path = event_data.get("file_path")

        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(self, "Грешка", f"Файлът не е намерен:\n{file_path}")
            return
        
        if sys.platform == "win32":
            os.startfile(file_path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", file_path])
        else:
            subprocess.Popen(["xdg-open", file_path])

    def open_event_folder(self):
        page = self.created_pages.get("recordings")
        if not page: return
        selected_items = page.list_widget.selectedItems()
        if not selected_items: return
        
        event_data = selected_items[0].data(Qt.ItemDataRole.UserRole)
        file_path_str = event_data.get("file_path")

        if not file_path_str or not os.path.exists(file_path_str):
            QMessageBox.warning(self, "Грешка", f"Файлът не е намерен:\n{file_path_str}")
            return
        
        folder_path = os.path.dirname(file_path_str)
        
        if sys.platform == "win32":
            os.startfile(folder_path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", folder_path])
        else:
            subprocess.Popen(["xdg-open", folder_path])

    def show_event_info(self):
        page = self.created_pages.get("recordings")
        if not page: return
        selected_items = page.list_widget.selectedItems()
        if not selected_items: return
        
        event_data = selected_items[0].data(Qt.ItemDataRole.UserRole)
        file_path = event_data.get("file_path")

        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(self, "Грешка", f"Файлът не е намерен:\n{file_path}")
            return
        
        info_dialog = InfoDialog(file_path, parent=self)
        info_dialog.exec()

    def delete_event(self, remote_event_id=None):
        page = self.created_pages.get("recordings")
        if not page and not remote_event_id: return

        event_to_delete = None

        if remote_event_id:
            all_events = DataManager.load_events()
            event_to_delete = next((e for e in all_events if e.get("event_id") == remote_event_id), None)
            if not event_to_delete:
                print(f"Remote delete request for non-existent event ID: {remote_event_id}")
                return
            self._perform_delete(event_to_delete)
            return

        selected_items = page.list_widget.selectedItems()
        if not selected_items: return
        event_to_delete = selected_items[0].data(Qt.ItemDataRole.UserRole)

        if self.is_remote_mode:
            payload = {"event_id": event_to_delete.get("event_id")}
            self.remote_client.send_action("delete_event", payload)
            QTimer.singleShot(500, self.refresh_recordings_view)
            return

        reply = QMessageBox.question(self, "Потвърждение", f"Сигурни ли сте, че искате да изтриете записа?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self._perform_delete(event_to_delete)

    def _perform_delete(self, event_to_delete):
        all_events = DataManager.load_events()
        updated_events = [e for e in all_events if e.get("event_id") != event_to_delete.get("event_id")]
        
        try:
            file_to_delete = event_to_delete.get("file_path")
            if file_to_delete and os.path.exists(file_to_delete):
                os.remove(file_to_delete)
                print(f"Изтрит файл: {file_to_delete}")
        except Exception as e:
            print(f"Грешка при изтриване на файл: {e}")

        DataManager.save_events(updated_events)
        
        if "recordings" in self.created_pages and self.pages.currentWidget() == self.created_pages["recordings"]:
            self.refresh_recordings_view()


    def add_camera(self):
        dialog = CameraDialog(parent=self)
        if dialog.exec():
            new_data = dialog.get_data()
            if not new_data["name"] or not new_data["rtsp_url"]: return
            new_data["id"] = str(uuid.uuid4())
            cameras_data = DataManager.load_cameras()
            cameras_data.append(new_data)
            DataManager.save_cameras(cameras_data)
            self.refresh_cameras_view()

    def edit_camera(self):
        page = self.created_pages.get("cameras")
        if not page: return
        selected_items = page.list_widget.selectedItems()
        if not selected_items: return
        camera_to_edit = selected_items[0].data(Qt.ItemDataRole.UserRole)
        dialog = CameraDialog(camera_data=camera_to_edit, parent=self)
        if dialog.exec():
            updated_data = dialog.get_data()
            if not updated_data["name"] or not updated_data["rtsp_url"]: return
            cameras_data = DataManager.load_cameras()
            for i, cam in enumerate(cameras_data):
                if cam.get("id") == camera_to_edit.get("id"):
                    cameras_data[i].update(updated_data)
                    break
            DataManager.save_cameras(cameras_data)
            self.refresh_cameras_view()

    def delete_camera(self):
        page = self.created_pages.get("cameras")
        if not page: return
        selected_items = page.list_widget.selectedItems()
        if not selected_items: return
        camera_to_delete = selected_items[0].data(Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(self, "Потвърждение", f"Изтриване на '{camera_to_delete['name']}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            cameras_data = DataManager.load_cameras()
            updated_cameras = [c for c in cameras_data if c.get("id") != camera_to_delete.get("id")]
            DataManager.save_cameras(updated_cameras)
            self.refresh_cameras_view()

    def refresh_users_view(self):
        page = self.created_pages.get("users")
        if not page: return
        page.list_widget.clear()
        users_data = DataManager.load_users()
        for user in users_data:
            item_text = f"{user['username']} ({user['role']})"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, user)
            page.list_widget.addItem(item)
    
    def add_user(self):
        dialog = UserDialog(parent=self)
        if dialog.exec():
            new_data = dialog.get_data()
            if not new_data["username"] or not new_data["password"]:
                QMessageBox.warning(self, "Грешка", "Полетата не могат да бъдат празни.")
                return
            users = DataManager.load_users()
            if any(u['username'] == new_data['username'] for u in users):
                QMessageBox.warning(self, "Грешка", f"Потребител с име '{new_data['username']}' вече съществува.")
                return
            users.append(new_data)
            DataManager.save_users(users)
            self.refresh_users_view()

    def edit_user(self):
        page = self.created_pages.get("users")
        if not page: return
        selected_items = page.list_widget.selectedItems()
        if not selected_items: return
        user_to_edit = selected_items[0].data(Qt.ItemDataRole.UserRole)
        dialog = UserDialog(user_data=user_to_edit, parent=self)
        if dialog.exec():
            updated_data = dialog.get_data()
            if not updated_data["password"]:
                QMessageBox.warning(self, "Грешка", "Паролата не може да бъде празна.")
                return
            users = DataManager.load_users()
            for i, u in enumerate(users):
                if u['username'] == user_to_edit['username']:
                    users[i] = updated_data
                    break
            DataManager.save_users(users)
            self.refresh_users_view()

    def delete_user(self):
        page = self.created_pages.get("users")
        if not page: return
        selected_items = page.list_widget.selectedItems()
        if not selected_items: return
        user_to_delete = selected_items[0].data(Qt.ItemDataRole.UserRole)
        if user_to_delete['username'] == 'admin':
            QMessageBox.warning(self, "Грешка", "Администраторският акаунт не може да бъде изтрит.")
            return
        reply = QMessageBox.question(self, "Потвърждение", f"Сигурни ли сте, че искате да изтриете '{user_to_delete['username']}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            users = DataManager.load_users()
            users = [u for u in users if u['username'] != user_to_delete['username']]
            DataManager.save_users(users)
            self.refresh_users_view()

    def closeEvent(self, event):
        self.stop_all_streams()
        if self.scanner: self.scanner.cancel()
        event.accept()
    
    def update_grid_layout(self):
        page = self.created_pages.get("live_view")
        if not page: return
        
        for widget in self.active_video_widgets.values():
            widget.hide()
            widget.setParent(None)

        all_widgets = list(self.active_video_widgets.values())
        widgets_to_show = []

        if page.grid_1x1_button.isChecked():
            page.camera_selector.show()
            selected_cam_id = page.camera_selector.currentData()
            widget_to_show = self.active_video_widgets.get(selected_cam_id)
            if widget_to_show:
                widgets_to_show.append(widget_to_show)
            cols = 1
        else:
            page.camera_selector.hide()
            cols = 2 if page.grid_2x2_button.isChecked() else 3
            limit = 4 if page.grid_2x2_button.isChecked() else 9
            widgets_to_show = all_widgets[:limit]

        if not widgets_to_show: return

        while page.grid_layout.count():
            child = page.grid_layout.takeAt(0)
            if child.widget():
                child.widget().setParent(None)

        for idx, widget in enumerate(widgets_to_show):
            row, col = idx // cols, idx % cols
            page.grid_layout.addWidget(widget, row, col)
            widget.show()

    def toggle_fullscreen_camera(self):
        sender_widget = self.sender()
        is_fullscreen = sender_widget.property("fullscreen")
        page = self.created_pages.get("live_view")
        if not page: return
        if is_fullscreen:
            for widget in self.active_video_widgets.values():
                widget.setProperty("fullscreen", False)
            self.update_grid_layout()
        else:
            for widget in self.active_video_widgets.values():
                if widget == sender_widget:
                    widget.setProperty("fullscreen", True)
                    page.grid_layout.addWidget(widget, 0, 0)
                    widget.show()
                else:
                    widget.hide()
                    
    def on_motion_detected(self, cam_id):
        widget = self.active_video_widgets.get(cam_id)
        if widget:
            widget.set_motion_state(True)
            
    def get_camera_to_control(self, remote_camera_id=None):
        if remote_camera_id:
             return self.video_workers.get(remote_camera_id), self.active_video_widgets.get(remote_camera_id)

        page = self.created_pages.get("live_view")
        if not page: return None, None
        
        if self.is_remote_mode and page.grid_1x1_button.isChecked():
            cam_id = page.camera_selector.currentData()
            return None, self.active_video_widgets.get(cam_id)

        if not self.active_video_widgets: return None, None
        
        cam_id = None
        if page.grid_1x1_button.isChecked():
            cam_id = page.camera_selector.currentData()
        else:
            if self.active_video_widgets:
                for i in range(page.grid_layout.count()):
                    widget = page.grid_layout.itemAt(i).widget()
                    if widget and widget.isVisible():
                        cam_id = widget.camera_id
                        break
        if cam_id:
            return self.video_workers.get(cam_id), self.active_video_widgets.get(cam_id)
        return None, None
            
    def sanitize_filename(self, name):
        """Премахва невалидни символи от низ, за да стане валидно име на файл."""
        return "".join(c for c in name if c.isalnum() or c in (' ', '.', '_')).rstrip()

    def get_recording_path_for_camera(self, worker):
        """Определя пътя за запис спрямо текущите настройки."""
        settings = DataManager.load_settings()
        base_path = Path(settings.get("recording_path"))
        structure = settings.get("recording_structure", "single")
        
        if structure == "per_camera":
            safe_camera_name = self.sanitize_filename(worker.camera_data['name'])
            camera_path = base_path / safe_camera_name
            camera_path.mkdir(parents=True, exist_ok=True)
            return camera_path
        else: # "single"
            base_path.mkdir(parents=True, exist_ok=True)
            return base_path

    def get_visible_widgets(self):
        visible_widgets = []
        page = self.created_pages.get("live_view")
        if not page: return visible_widgets
        for i in range(page.grid_layout.count()):
            widget = page.grid_layout.itemAt(i).widget()
            if widget and widget.isVisible():
                visible_widgets.append(widget)
        return visible_widgets

    def take_snapshot(self, remote_camera_id=None):
        page = self.created_pages.get("live_view")
        if not page: return

        cam_id = None
        if remote_camera_id:
            cam_id = remote_camera_id
        elif page.grid_1x1_button.isChecked():
            cam_id = page.camera_selector.currentData()
        else:
            cam_id = "grid"
        
        if self.is_remote_mode:
            payload = {"camera_id": cam_id}
            self.remote_client.send_action("snapshot", payload)
            print(f"Изпратена заявка за снимка към отдалечена система за камера: {cam_id}")
            return

        if cam_id == "grid":
            visible_widgets = self.get_visible_widgets()
            if not visible_widgets: return
            cols = 2 if page.grid_2x2_button.isChecked() else 3
            rows = (len(visible_widgets) + cols - 1) // cols
            
            first_worker = self.video_workers.get(visible_widgets[0].camera_id)
            if not first_worker: return
            sample_frame = first_worker.get_latest_frame()
            if sample_frame is None: return
            h, w, _ = sample_frame.shape

            canvas = np.zeros((h * rows, w * cols, 3), dtype=np.uint8)
            for i, widget in enumerate(visible_widgets):
                worker = self.video_workers.get(widget.camera_id)
                if worker:
                    frame = worker.get_latest_frame()
                    if frame is not None:
                        row, col = i // cols, i % cols
                        canvas[row*h:(row+1)*h, col*w:(col+1)*w] = frame

            settings = DataManager.load_settings()
            recording_path = Path(settings.get("recording_path"))
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = recording_path / f"snap_grid_{timestamp}.jpg"
            cv2.imwrite(str(filename), canvas)
            print(f"Снимка на мрежата е запазена: {filename}")
            self.add_event("grid", "Снимка (мрежа)", str(filename))
        else:
            worker, _ = self.get_camera_to_control(remote_camera_id=cam_id)
            if worker:
                frame = worker.get_latest_frame()
                if frame is not None:
                    recording_path = self.get_recording_path_for_camera(worker)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    safe_name = self.sanitize_filename(worker.camera_data['name'])
                    filename = recording_path / f"snap_{safe_name}_{timestamp}.jpg"
                    cv2.imwrite(str(filename), frame)
                    print(f"Снимка запазена: {filename}")
                    self.add_event(worker.camera_data['id'], "Снимка", str(filename))

    def toggle_manual_recording(self, is_recording, remote_camera_id=None):
        page = self.created_pages.get("live_view")
        if not page: return

        cam_id = None
        if remote_camera_id:
             cam_id = remote_camera_id
        elif page.grid_1x1_button.isChecked():
            cam_id = page.camera_selector.currentData()
        else:
            cam_id = "grid"

        if self.is_remote_mode:
            payload = {"camera_id": cam_id, "state": is_recording}
            self.remote_client.send_action("toggle_record", payload)
            print(f"Изпратена заявка за запис към отдалечена система за камера: {cam_id}, състояние: {is_recording}")
            return
            
        if cam_id == "grid":
             if is_recording: self.start_grid_recording()
             else: self.stop_grid_recording()
        else:
            self.toggle_single_camera_recording(is_recording, remote_camera_id=cam_id)

    def toggle_single_camera_recording(self, is_recording, remote_camera_id=None):
        page = self.created_pages.get("live_view")
        worker, widget = self.get_camera_to_control(remote_camera_id=remote_camera_id)
        if not worker or not widget: 
            if page and not remote_camera_id: page.record_button.setChecked(False)
            return

        if is_recording:
            if not remote_camera_id:
                page.record_button.setText(self.translator.get_string("stop_record_button"))
            if self.recording_worker: return
            recording_path = self.get_recording_path_for_camera(worker)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = self.sanitize_filename(worker.camera_data['name'])
            filename = recording_path / f"rec_{safe_name}_{timestamp}.mp4"
            frame = worker.get_latest_frame()
            if frame is None:
                if page and not remote_camera_id: page.record_button.setChecked(False)
                return
            height, width, _ = frame.shape
            recording_fps = 20.0
            self.recording_worker = RecordingWorker(str(filename), width, height, recording_fps)
            worker.FrameForRecording.connect(self.handle_single_frame_for_recording)
            self.recording_worker.start()
            widget.set_recording_state(True)
            self.add_event(worker.camera_data['id'], "Ръчен запис", str(filename))
            print(f"Ръчен запис стартиран: {filename}")
        else:
            if not remote_camera_id:
                page.record_button.setText(self.translator.get_string("record_button"))
            if self.recording_worker:
                try: worker.FrameForRecording.disconnect(self.handle_single_frame_for_recording)
                except (TypeError, RuntimeError): pass
                self.recording_worker.stop()
                self.recording_worker.wait()
                self.recording_worker = None
                if widget: widget.set_recording_state(False)
                print("Ръчен запис спрян.")
    
    def handle_single_frame_for_recording(self, cam_id, frame):
        if self.recording_worker and self.recording_worker.isRunning():
            self.recording_worker.add_frame(frame)

    def start_grid_recording(self):
        page = self.created_pages.get("live_view")
        if not page: return
        
        page.record_button.setText(self.translator.get_string("stop_record_button"))
        if self.is_grid_recording: return

        visible_widgets = self.get_visible_widgets()
        if not visible_widgets:
            page.record_button.setChecked(False)
            return

        first_worker = self.video_workers.get(visible_widgets[0].camera_id)
        if not first_worker: return
        sample_frame = first_worker.get_latest_frame()
        if sample_frame is None: return
        h, w, _ = sample_frame.shape
        
        cols = 2 if page.grid_2x2_button.isChecked() else 3
        rows = (len(visible_widgets) + cols - 1) // cols
        
        settings = DataManager.load_settings()
        recording_path = Path(settings.get("recording_path"))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = recording_path / f"rec_grid_{timestamp}.mp4"
        
        recording_fps = 20.0
        self.recording_worker = RecordingWorker(str(filename), w * cols, h * rows, recording_fps)
        
        self.latest_grid_frames.clear()
        for widget in visible_widgets:
            worker = self.video_workers.get(widget.camera_id)
            if worker:
                worker.FrameForRecording.connect(self._update_latest_grid_frame)
        
        self.grid_recording_timer.start(1000 / recording_fps)
        self.recording_worker.start()
        self.is_grid_recording = True
        
        for widget in visible_widgets:
            widget.set_recording_state(True)

        self.add_event("grid", "Запис (мрежа)", str(filename))
        print(f"Запис на мрежата стартиран: {filename}")

    def stop_grid_recording(self):
        page = self.created_pages.get("live_view")
        if not page: return
        
        page.record_button.setText(self.translator.get_string("record_button"))
        if not self.is_grid_recording: return

        self.grid_recording_timer.stop()
        
        for worker in self.video_workers.values():
            try: worker.FrameForRecording.disconnect(self._update_latest_grid_frame)
            except (TypeError, RuntimeError): pass

        if self.recording_worker:
            self.recording_worker.stop()
            self.recording_worker.wait()
            self.recording_worker = None

        self.is_grid_recording = False
        
        for widget in self.get_visible_widgets():
            widget.set_recording_state(False)
            
        print("Запис на мрежата спрян.")

    def _update_latest_grid_frame(self, cam_id, frame):
        self.latest_grid_frames[cam_id] = frame

    def _compose_and_record_grid_frame(self):
        page = self.created_pages.get("live_view")
        if not page or not self.is_grid_recording:
            return
            
        visible_widgets = self.get_visible_widgets()
        if not visible_widgets: return

        first_worker = self.video_workers.get(visible_widgets[0].camera_id)
        if not first_worker: return
        sample_frame = first_worker.get_latest_frame()
        if sample_frame is None: return
        h, w, _ = sample_frame.shape

        cols = 2 if page.grid_2x2_button.isChecked() else 3
        rows = (len(visible_widgets) + cols - 1) // cols
        
        canvas = np.zeros((h * rows, w * cols, 3), dtype=np.uint8)

        for i, widget in enumerate(visible_widgets):
            frame = self.latest_grid_frames.get(widget.camera_id)
            if frame is not None:
                row, col = i // cols, i % cols
                resized_frame = cv2.resize(frame, (w, h))
                canvas[row*h:(row+1)*h, col*w:(col+1)*w] = resized_frame
        
        if self.recording_worker:
            self.recording_worker.add_frame(canvas)

    def add_event(self, camera_id, event_type, file_path):
        cameras = self.load_cameras()
        if cameras is None: return
        
        camera_name = "Неизвестна камера"
        if camera_id == "grid":
            camera_name = "Мрежа"
        else:
            cam = next((c for c in cameras if c.get("id") == camera_id), None)
            if cam:
                camera_name = cam.get("name")
        
        new_event = {
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "camera_name": camera_name,
            "event_type": event_type,
            "file_path": str(file_path)
        }
        all_events = DataManager.load_events()
        all_events.insert(0, new_event)
        DataManager.save_events(all_events)
    
    def show_remote_systems_dialog(self):
        """Показва диалога за управление на отдалечени системи."""
        dialog = RemoteSystemsPage(parent=self)
        dialog.connection_successful.connect(self.connect_to_remote_system)
        dialog.exec()

    def connect_to_remote_system(self, client):
        """Превключва приложението в отдалечен режим."""
        self.stop_all_streams()
        self.is_remote_mode = True
        self.remote_client = client
        
        self.btn_remote.hide()
        self.btn_disconnect.show()
        
        self.setWindowTitle(f"{self.translator.get_string('main_window_title')} - [ОТДАЛЕЧЕН РЕЖИМ]")
        
        current_page_widget = self.pages.currentWidget()
        if hasattr(current_page_widget, 'page_name'):
            page_name = current_page_widget.page_name
            self.switch_to_page(page_name)

    def disconnect_from_remote(self):
        """Превключва приложението обратно в локален режим."""
        self.is_remote_mode = False
        self.remote_client = None
        
        self.stop_all_streams()
        
        self.btn_remote.show()
        self.btn_disconnect.hide()
        self.setWindowTitle(self.translator.get_string("main_window_title"))

        current_page_widget = self.pages.currentWidget()
        if hasattr(current_page_widget, 'page_name'):
            page_name = current_page_widget.page_name
            self.switch_to_page(page_name)