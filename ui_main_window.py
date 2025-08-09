import uuid
import os
import subprocess
import sys
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QStackedWidget, QLabel, QMessageBox, QProgressDialog, QListWidgetItem
)
from PySide6.QtCore import QSize, Qt, QThread, QTimer
from PySide6.QtGui import QIcon

from data_manager import DataManager
from ui_pages import CamerasPage, LiveViewPage, RecordingsPage, SettingsPage
from ui_dialogs import CameraDialog
from network_scanner import NetworkScanner, get_local_subnet
from video_worker import VideoWorker
from ui_widgets import VideoFrame

class MainWindow(QMainWindow):
    def __init__(self, base_dir):
        super().__init__()
        self.base_dir = base_dir
        self.setWindowTitle("TSA-Security")
        self.setGeometry(100, 100, 1280, 720)

        self.video_workers = {}
        self.active_video_widgets = {}
        self.created_pages = {}

        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setCentralWidget(main_widget)

        sidebar = QWidget()
        sidebar.setFixedWidth(200)
        sidebar.setStyleSheet("background-color: #2D2D30;")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(10, 10, 10, 10)
        sidebar_layout.setSpacing(10)

        self.pages = QStackedWidget()
        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.pages)
        
        btn_live_view = self.create_nav_button("Изглед на живо", "icons/video-camera.png")
        btn_cameras = self.create_nav_button("Камери", "icons/camera.png")
        btn_recordings = self.create_nav_button("Записи", "icons/archive.png")
        btn_settings = self.create_nav_button("Настройки", "icons/gear.png")

        sidebar_layout.addWidget(btn_live_view)
        sidebar_layout.addWidget(btn_cameras)
        sidebar_layout.addWidget(btn_recordings)
        sidebar_layout.addStretch()
        sidebar_layout.addWidget(btn_settings)

        btn_live_view.clicked.connect(self.show_live_view_page)
        btn_cameras.clicked.connect(self.show_cameras_page)
        btn_recordings.clicked.connect(self.show_recordings_page)
        btn_settings.clicked.connect(self.show_settings_page)
        
        btn_live_view.setChecked(True)
        self.show_live_view_page()
    
    def switch_to_page(self, page_name):
        current_widget = self.pages.currentWidget()
        if hasattr(current_widget, 'page_name') and current_widget.page_name == "live_view":
             self.stop_all_streams()

        self.pages.setCurrentWidget(self.created_pages[page_name])
        
        if page_name == "live_view":
            self.start_all_streams()
        elif page_name == "recordings":
            self.setup_recordings_page()
        elif page_name == "cameras":
            self.refresh_cameras_view()
        elif page_name == "settings":
            self.load_settings()

    def show_live_view_page(self):
        page_name = "live_view"
        if page_name not in self.created_pages:
            page = LiveViewPage()
            page.page_name = page_name
            page.grid_1x1_button.clicked.connect(self.update_grid_layout)
            page.grid_2x2_button.clicked.connect(self.update_grid_layout)
            page.grid_3x3_button.clicked.connect(self.update_grid_layout)
            self.created_pages[page_name] = page
            self.pages.addWidget(page)
        self.switch_to_page(page_name)

    def show_cameras_page(self):
        page_name = "cameras"
        if page_name not in self.created_pages:
            page = CamerasPage()
            page.page_name = page_name
            page.add_button.clicked.connect(self.add_camera)
            page.edit_button.clicked.connect(self.edit_camera)
            page.delete_button.clicked.connect(self.delete_camera)
            self.created_pages[page_name] = page
            self.pages.addWidget(page)
        self.switch_to_page(page_name)

    def show_recordings_page(self):
        page_name = "recordings"
        if page_name not in self.created_pages:
            page = RecordingsPage()
            page.page_name = page_name
            self.created_pages[page_name] = page
            self.pages.addWidget(page)
        self.switch_to_page(page_name)
    
    def setup_recordings_page(self):
        page = self.created_pages.get("recordings")
        if not page or hasattr(page, 'is_setup'): return
        
        page.view_button.clicked.connect(self.view_event)
        page.delete_button.clicked.connect(self.delete_event)
        page.camera_filter.currentIndexChanged.connect(self.apply_event_filters)
        page.event_type_filter.currentIndexChanged.connect(self.apply_event_filters)
        
        self.refresh_recordings_view()
        page.is_setup = True

    def show_settings_page(self):
        page_name = "settings"
        if page_name not in self.created_pages:
            page = SettingsPage()
            page.page_name = page_name
            page.save_button.clicked.connect(self.save_settings)
            self.created_pages[page_name] = page
            self.pages.addWidget(page)
        self.switch_to_page(page_name)
    
    # --- МЕТОДИ ЗА НАСТРОЙКИ (ЛИПСВАЩИТЕ МЕТОДИ СА ТУК) ---
    def load_settings(self):
        """Зарежда настройките и ги показва в интерфейса."""
        page = self.created_pages.get("settings")
        if not page: return

        settings_data = DataManager.load_settings()
        
        page.theme_combo.setCurrentText("Тъмна" if settings_data.get("theme") == "dark" else "Светла")
        page.grid_combo.setCurrentText(settings_data.get("default_grid", "2x2"))
        page.path_edit.setText(settings_data.get("recording_path", ""))

    def save_settings(self):
        """Взима данните от интерфейса и ги записва във файла."""
        page = self.created_pages.get("settings")
        if not page: return
        
        new_settings = {
            "theme": "dark" if page.theme_combo.currentText() == "Тъмна" else "light",
            "default_grid": page.grid_combo.currentText(),
            "recording_path": page.path_edit.text()
        }
        
        DataManager.save_settings(new_settings)
        
        QMessageBox.information(self, "Успех", "Настройките бяха запазени успешно!")
        
    # --- Други методи ---
    def start_all_streams(self):
        if self.video_workers: return
        cameras_data = DataManager.load_cameras()
        active_cameras = [cam for cam in cameras_data if cam.get("is_active")]
        for cam_data in active_cameras:
            cam_id = cam_data.get("id")
            frame_widget = VideoFrame(camera_name=cam_data.get("name"), camera_id=cam_id)
            frame_widget.double_clicked.connect(self.toggle_fullscreen_camera)
            worker = VideoWorker(rtsp_url=cam_data.get("rtsp_url"))
            worker.ImageUpdate.connect(frame_widget.update_frame)
            worker.StreamStatus.connect(frame_widget.update_status)
            worker.start()
            self.video_workers[cam_id] = worker
            self.active_video_widgets[cam_id] = frame_widget
        self.update_grid_layout()

    def stop_all_streams(self):
        if not self.video_workers: return
        for worker in self.video_workers.values():
            worker.stop()
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
            item_text = f"{cam['name']} ({'Активна' if cam['is_active'] else 'Неактивна'})"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, cam)
            page.list_widget.addItem(item)
    
    def refresh_recordings_view(self):
        page = self.created_pages.get("recordings")
        if not page: return

        all_events = DataManager.load_events()
        cameras = sorted(list(set(event.get("camera_name") for event in all_events)))
        event_types = sorted(list(set(event.get("event_type") for event in all_events)))
        page.camera_filter.blockSignals(True)
        page.event_type_filter.blockSignals(True)
        page.camera_filter.clear()
        page.event_type_filter.clear()
        page.camera_filter.addItem("Всички камери")
        page.event_type_filter.addItem("Всички типове")
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
        if "Всички" in cam_filter: cam_filter = ""
        if "Всички" in type_filter: type_filter = ""
        
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
    
    def view_event(self):
        page = self.created_pages.get("recordings")
        if not page: return
        selected_items = page.list_widget.selectedItems()
        if not selected_items: return
        
        event_data = selected_items[0].data(Qt.ItemDataRole.UserRole)
        file_path = event_data.get("file_path")

        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(self, "Грешка", f"Файлът не е намерен:\n{file_path}")
            return
        
        if sys.platform == "win32": os.startfile(file_path)
        elif sys.platform == "darwin": subprocess.Popen(["open", file_path])
        else: subprocess.Popen(["xdg-open", file_path])

    def delete_event(self):
        page = self.created_pages.get("recordings")
        if not page: return
        selected_items = page.list_widget.selectedItems()
        if not selected_items: return

        event_to_delete = selected_items[0].data(Qt.ItemDataRole.UserRole)
        
        reply = QMessageBox.question(self, "Потвърждение", "Сигурни ли сте?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
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

        reply = QMessageBox.question(self, "Потвърждение", f"Изтриване на '{camera_to_delete['name']}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            cameras_data = DataManager.load_cameras()
            updated_cameras = [c for c in cameras_data if c.get("id") != camera_to_delete.get("id")]
            DataManager.save_cameras(updated_cameras)
            self.refresh_cameras_view()

    def create_nav_button(self, text, relative_icon_path):
        button = QPushButton(text)
        button.setObjectName("NavButton")
        button.setCheckable(True)
        button.setAutoExclusive(True)
        full_icon_path = self.base_dir / relative_icon_path
        if full_icon_path.exists():
            button.setIcon(QIcon(str(full_icon_path)))
        else:
            print(f"Предупреждение: Иконата не е намерена: {full_icon_path}")
        button.setIconSize(QSize(24, 24))
        return button

    def closeEvent(self, event):
        self.stop_all_streams()
        event.accept()

    def update_grid_layout(self):
        page = self.created_pages.get("live_view")
        if not page: return
        
        for widget in self.active_video_widgets.values():
            widget.hide()
            widget.setParent(None)

        all_widgets = list(self.active_video_widgets.values())
        widgets_to_show = []
        cols = 1

        if page.grid_1x1_button.isChecked():
            cols = 1; widgets_to_show = all_widgets[:1]
        elif page.grid_2x2_button.isChecked():
            cols = 2; widgets_to_show = all_widgets[:4]
        elif page.grid_3x3_button.isChecked():
            cols = 3; widgets_to_show = all_widgets[:9]

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
                    
    def scan_network(self):
        pass