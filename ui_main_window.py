import uuid
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime
import cv2
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QStackedWidget, QLabel, QMessageBox, QProgressDialog, QListWidgetItem
)
from PySide6.QtCore import QSize, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QIcon

from data_manager import DataManager, get_translator
from ui_pages import CamerasPage, LiveViewPage, RecordingsPage, SettingsPage, UsersPage
from ui_dialogs import CameraDialog, UserDialog
from video_worker import VideoWorker, RecordingWorker
from ui_widgets import VideoFrame
from network_scanner import NetworkScanner, get_local_subnet
from ui_media_viewer import MediaViewerDialog
from ui_info_dialog import InfoDialog

class MainWindow(QMainWindow):
    logout_requested = Signal()
    restart_requested = Signal()

    def __init__(self, base_dir, user_role):
        super().__init__()
        self.translator = get_translator()
        self.base_dir = base_dir
        self.user_role = user_role
        
        self.setWindowTitle(self.translator.get_string("main_window_title"))
        self.setGeometry(100, 100, 1280, 720)

        self.video_workers = {}
        self.active_video_widgets = {}
        self.recording_worker = None
        self.created_pages = {}
        
        self.scanner_thread = None
        self.scanner = None
        self.progress_dialog = None

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
        btn_logout = self.create_nav_button(self.translator.get_string("logout"), "icons/logout.png")

        sidebar_layout.addWidget(btn_live_view)
        sidebar_layout.addWidget(btn_cameras)
        sidebar_layout.addWidget(btn_recordings)
        sidebar_layout.addStretch()
        sidebar_layout.addWidget(self.btn_users)
        sidebar_layout.addWidget(btn_settings)
        sidebar_layout.addWidget(btn_logout)

        btn_live_view.clicked.connect(self.show_live_view_page)
        btn_cameras.clicked.connect(self.show_cameras_page)
        btn_recordings.clicked.connect(self.show_recordings_page)
        self.btn_users.clicked.connect(self.show_users_page)
        btn_settings.clicked.connect(self.show_settings_page)
        btn_logout.clicked.connect(self.logout_requested.emit)
        
        self.apply_role_permissions()
        
        btn_live_view.setChecked(True)
        self.show_live_view_page()
    
    def create_nav_button(self, text, relative_icon_path):
        button = QPushButton(text)
        button.setObjectName("NavButton")
        if "logout" not in relative_icon_path:
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
                if self.user_role != "Administrator":
                    page.add_button.hide()
                    page.edit_button.hide()
                    page.delete_button.hide()
                    page.scan_button.hide()
                    page.search_input.hide()
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
    def show_settings_page(self): self.switch_to_page("settings")
    def show_users_page(self):
        if self.user_role == "Administrator": self.switch_to_page("users")

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
        
        if self.user_role != "Administrator":
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
        if self.video_workers: return
        page = self.created_pages.get("live_view")
        if not page: return
        page.camera_selector.clear()
        cameras_data = DataManager.load_cameras()
        active_cameras = [cam for cam in cameras_data if cam.get("is_active")]
        for cam_data in active_cameras:
            cam_id = cam_data.get("id")
            page.camera_selector.addItem(cam_data["name"], cam_id)
            frame_widget = VideoFrame(camera_name=cam_data.get("name"), camera_id=cam_id)
            frame_widget.double_clicked.connect(self.toggle_fullscreen_camera)
            self.start_single_worker(cam_data, frame_widget)
            self.active_video_widgets[cam_id] = frame_widget
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

    def handle_worker_finished(self, cam_id):
        print(f"Нишката за камера {cam_id} приключи. Рестартиране след 5 секунди...")
        if cam_id in self.video_workers:
            self.video_workers.pop(cam_id, None)
            cameras_data = DataManager.load_cameras()
            cam_data = next((c for c in cameras_data if c.get("id") == cam_id), None)
            frame_widget = self.active_video_widgets.get(cam_id)
            if cam_data and frame_widget:
                QTimer.singleShot(5000, lambda: self.start_single_worker(cam_data, frame_widget))

    def stop_all_streams(self):
        if self.recording_worker:
            worker, _ = self.get_camera_to_control()
            if worker:
                try: worker.FrameForRecording.disconnect(self.recording_worker.add_frame)
                except (TypeError, RuntimeError): pass
            self.recording_worker.stop()
            self.recording_worker.wait()
            self.recording_worker = None
        if not self.video_workers: return
        for worker in self.video_workers.values():
            worker.stop()
            worker.wait()
        self.video_workers.clear()
        for widget in self.active_video_widgets.values():
            widget.deleteLater()
        self.active_video_widgets.clear()
    
    def refresh_cameras_view(self):
        page = self.created_pages.get("cameras")
        if not page: return
        page.list_widget.clear()
        cameras_data = DataManager.load_cameras()
        for cam in cameras_data:
            status = self.translator.get_string("camera_status_active") if cam.get('is_active') else self.translator.get_string("camera_status_inactive")
            motion = self.translator.get_string("motion_detection_on") if cam.get('motion_enabled') else self.translator.get_string("motion_detection_off")
            item_text = f"{cam['name']} - {status} - {motion}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, cam)
            page.list_widget.addItem(item)
    
    def refresh_recordings_view(self):
        page = self.created_pages.get("recordings")
        if not page: return
        
        page.view_in_app_button.setText("Преглед в програмата")
        page.open_in_player_button.setText("Отваряне в плейър")
        page.open_folder_button.setText(self.translator.get_string("open_folder_button"))
        page.info_button.setText("Информация")

        all_events = DataManager.load_events()
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
        all_events = DataManager.load_events()
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
        file_path = event_data.get("file_path")

        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(self, "Грешка", f"Файлът не е намерен:\n{file_path}")
            return
        
        viewer = MediaViewerDialog(file_path, parent=self)
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

    def delete_event(self):
        page = self.created_pages.get("recordings")
        if not page: return
        selected_items = page.list_widget.selectedItems()
        if not selected_items: return
        event_to_delete = selected_items[0].data(Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(self, "Потвърждение", "Сигурни ли сте?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            all_events = DataManager.load_events()
            updated_events = [e for e in all_events if e.get("event_id") != event_to_delete.get("event_id")]
            DataManager.save_events(updated_events)
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
            if selected_cam_id and selected_cam_id in self.active_video_widgets:
                widgets_to_show.append(self.active_video_widgets[selected_cam_id])
            cols = 1
        else:
            page.camera_selector.hide()
            cols = 2 if page.grid_2x2_button.isChecked() else 3
            limit = 4 if page.grid_2x2_button.isChecked() else 9
            widgets_to_show = all_widgets[:limit]
        if not widgets_to_show: return
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
            
    def get_camera_to_control(self):
        page = self.created_pages.get("live_view")
        if not page or not self.active_video_widgets:
            return None, None
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

    def take_snapshot(self):
        worker, _ = self.get_camera_to_control()
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

    def toggle_manual_recording(self, is_recording):
        page = self.created_pages.get("live_view")
        if not page: return
        worker, widget = self.get_camera_to_control()
        if not worker or not widget: 
            page.record_button.setChecked(False)
            return
        if is_recording:
            page.record_button.setText(self.translator.get_string("stop_record_button"))
            if self.recording_worker: return
            recording_path = self.get_recording_path_for_camera(worker)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = self.sanitize_filename(worker.camera_data['name'])
            filename = recording_path / f"rec_{safe_name}_{timestamp}.mp4"
            frame = worker.get_latest_frame()
            if frame is None:
                page.record_button.setChecked(False)
                return
            height, width, _ = frame.shape
            recording_fps = 20.0
            print(f"Starting recording with fixed FPS: {recording_fps}")
            self.recording_worker = RecordingWorker(str(filename), width, height, recording_fps)
            worker.FrameForRecording.connect(self.recording_worker.add_frame)
            self.recording_worker.start()
            widget.set_recording_state(True)
            self.add_event(worker.camera_data['id'], "Ръчен запис", str(filename))
            print(f"Ръчен запис стартиран: {filename}")
        else:
            page.record_button.setText(self.translator.get_string("record_button"))
            if self.recording_worker:
                try:
                    worker.FrameForRecording.disconnect(self.recording_worker.add_frame)
                except (TypeError, RuntimeError): pass
                self.recording_worker.stop()
                self.recording_worker.wait()
                self.recording_worker = None
                if widget: widget.set_recording_state(False)
                print("Ръчен запис спрян.")

    def add_event(self, camera_id, event_type, file_path):
        cameras = DataManager.load_cameras()
        camera_name = "Неизвестна камера"
        for cam in cameras:
            if cam.get("id") == camera_id:
                camera_name = cam.get("name")
                break
        new_event = { "event_id": str(uuid.uuid4()), "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "camera_name": camera_name, "event_type": event_type, "file_path": str(file_path) }
        all_events = DataManager.load_events()
        all_events.insert(0, new_event)
        DataManager.save_events(all_events)