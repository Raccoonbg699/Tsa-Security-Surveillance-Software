import uuid
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QStackedWidget, QLabel, QMessageBox, QProgressDialog
)
from PySide6.QtCore import QSize, Qt, QThread
from PySide6.QtGui import QIcon

from data_manager import DataManager
from models import CameraTableModel
from ui_pages import CamerasPage, LiveViewPage
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

        self.cameras_data = DataManager.load_cameras()
        self.video_workers = {}
        self.active_video_widgets = {}
        self.scanner_thread = None
        self.scanner = None

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

        btn_live_view = self.create_nav_button("Изглед на живо", "icons/video-camera.png")
        btn_cameras = self.create_nav_button("Камери", "icons/camera.png")
        btn_recordings = self.create_nav_button("Записи", "icons/archive.png")
        btn_settings = self.create_nav_button("Настройки", "icons/gear.png")

        sidebar_layout.addWidget(btn_live_view)
        sidebar_layout.addWidget(btn_cameras)
        sidebar_layout.addWidget(btn_recordings)
        sidebar_layout.addStretch()
        sidebar_layout.addWidget(btn_settings)

        self.pages = QStackedWidget()
        btn_live_view.clicked.connect(lambda: self.pages.setCurrentIndex(0))
        btn_cameras.clicked.connect(lambda: self.pages.setCurrentIndex(1))
        btn_recordings.clicked.connect(lambda: self.pages.setCurrentIndex(2))
        btn_settings.clicked.connect(lambda: self.pages.setCurrentIndex(3))

        self.page_live_view = LiveViewPage()
        self.page_live_view.grid_1x1_button.clicked.connect(self.update_grid_layout)
        self.page_live_view.grid_2x2_button.clicked.connect(self.update_grid_layout)
        self.page_live_view.grid_3x3_button.clicked.connect(self.update_grid_layout)

        self.camera_table_model = CameraTableModel(self.cameras_data)
        self.page_cameras = CamerasPage(self.camera_table_model)

        page_recordings = QLabel("Страница 'Записи'")
        page_recordings.setAlignment(Qt.AlignmentFlag.AlignCenter)
        page_settings = QLabel("Страница 'Настройки'")
        page_settings.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.pages.addWidget(self.page_live_view)
        self.pages.addWidget(self.page_cameras)
        self.pages.addWidget(page_recordings)
        self.pages.addWidget(page_settings)

        btn_live_view.setChecked(True)

        main_layout.addWidget(sidebar)
        main_layout.addWidget(self.pages)

        add_button = self.page_cameras.findChild(QPushButton, "qt_find_add_button")
        add_button.clicked.connect(self.add_camera)
        self.page_cameras.edit_button.clicked.connect(self.edit_camera)
        self.page_cameras.delete_button.clicked.connect(self.delete_camera)
        self.page_cameras.scan_button.clicked.connect(self.scan_network)

        self.start_all_streams()

    def update_grid_layout(self):
        """
        Пренарежда видео уиджетите според избрания изглед (НОВА ЛОГИКА).
        """
        # 1. Първо скриваме всички уиджети
        for widget in self.active_video_widgets.values():
            widget.hide()
            widget.setParent(None) # Премахваме ги от мрежата

        # 2. Взимаме списък с всички активни уиджети
        all_widgets = list(self.active_video_widgets.values())
        widgets_to_show = []
        cols = 1

        # 3. Определяме кои уиджети да се покажат и в колко колони
        if self.page_live_view.grid_1x1_button.isChecked():
            cols = 1
            widgets_to_show = all_widgets[:1]  # Взимаме само първия
        elif self.page_live_view.grid_2x2_button.isChecked():
            cols = 2
            widgets_to_show = all_widgets[:4]  # Взимаме до 4
        elif self.page_live_view.grid_3x3_button.isChecked():
            cols = 3
            widgets_to_show = all_widgets[:9]  # Взимаме до 9

        if not widgets_to_show:
            return

        # 4. Добавяме и показваме само избраните уиджети
        for idx, widget in enumerate(widgets_to_show):
            row, col = idx // cols, idx % cols
            self.page_live_view.grid_layout.addWidget(widget, row, col)
            widget.show()

    def start_all_streams(self):
        self.stop_all_streams()

        active_cameras = [cam for cam in self.cameras_data if cam.get("is_active")]

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
        for worker in self.video_workers.values():
            worker.stop()
        self.video_workers.clear()

        for widget in self.active_video_widgets.values():
            widget.deleteLater()
        self.active_video_widgets.clear()

    def toggle_fullscreen_camera(self):
        sender_widget = self.sender()
        sender_id = sender_widget.camera_id

        is_fullscreen = any(widget.property("fullscreen") for widget in self.active_video_widgets.values())

        if is_fullscreen:
            # Деактивираме fullscreen за всички
            for widget in self.active_video_widgets.values():
                widget.setProperty("fullscreen", False)
            # Връщаме нормалния изглед
            self.update_grid_layout()
        else:
            # Показваме само кликнатия уиджет
            for cam_id, widget in self.active_video_widgets.items():
                if cam_id == sender_id:
                    widget.setProperty("fullscreen", True)
                    # Преместваме го в клетка (0,0) на мрежата
                    self.page_live_view.grid_layout.addWidget(widget, 0, 0)
                    widget.show() # Уверяваме се, че е видим
                else:
                    widget.hide() # Скриваме всички останали

    def refresh_cameras_view(self):
        self.camera_table_model.update_data(self.cameras_data)
        DataManager.save_cameras(self.cameras_data)
        self.page_cameras.on_selection_changed()
        self.start_all_streams()

    def closeEvent(self, event):
        self.stop_all_streams()
        event.accept()

    def scan_network(self):
        subnet = get_local_subnet()
        if not subnet:
            QMessageBox.critical(self, "Грешка", "Не може да бъде определена локалната мрежа.")
            return

        self.progress_dialog = QProgressDialog("Сканиране на мрежата за камери...", "Прекрати", 0, 100, self)
        self.progress_dialog.setWindowTitle("Сканиране")
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)

        self.scanner_thread = QThread()
        self.scanner = NetworkScanner(subnet)
        self.scanner.moveToThread(self.scanner_thread)

        self.progress_dialog.canceled.connect(self.scanner.cancel)
        self.scanner.scan_progress.connect(self.progress_dialog.setValue)
        self.scanner.camera_found.connect(self.handle_found_camera)
        self.scanner.scan_finished.connect(self.on_scan_finished)

        self.scanner_thread.started.connect(self.scanner.run)
        self.page_cameras.scan_button.setEnabled(False)
        self.scanner_thread.start()
        self.progress_dialog.show()

    def handle_found_camera(self, ip_address):
        if any(cam.get('rtsp_url') and ip_address in cam.get('rtsp_url') for cam in self.cameras_data):
            print(f"Камера с IP {ip_address} вече съществува. Пропускане.")
            return

        reply = QMessageBox.question(self,
                                     "Намерена камера",
                                     f"Намерена е потенциална камера на адрес {ip_address}.\nЖелаете ли да я добавите?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            cam_data = {
                "name": f"Камера @ {ip_address}",
                "rtsp_url": f"rtsp://{ip_address}:554/",
                "is_active": True
            }
            dialog = CameraDialog(camera_data=cam_data, parent=self)
            if dialog.exec():
                new_data = dialog.get_data()
                new_data["id"] = str(uuid.uuid4())
                self.cameras_data.append(new_data)
                self.refresh_cameras_view()

    def on_scan_finished(self, message):
        print(message)
        self.progress_dialog.close()
        self.page_cameras.scan_button.setEnabled(True)
        if self.scanner_thread:
            self.scanner_thread.quit()
            self.scanner_thread.wait()

    def add_camera(self):
        dialog = CameraDialog(parent=self)
        if dialog.exec():
            new_data = dialog.get_data()
            if not new_data["name"] or not new_data["rtsp_url"]:
                QMessageBox.warning(self, "Грешка", "Името и RTSP адресът не могат да бъдат празни.")
                return
            new_data["id"] = str(uuid.uuid4())
            self.cameras_data.append(new_data)
            self.refresh_cameras_view()

    def edit_camera(self):
        selected_rows = self.page_cameras.table_view.selectionModel().selectedRows()
        if not selected_rows:
            return
        row_index = selected_rows[0].row()
        camera_to_edit = self.cameras_data[row_index]
        dialog = CameraDialog(camera_data=camera_to_edit, parent=self)
        if dialog.exec():
            updated_data = dialog.get_data()
            if not updated_data["name"] or not updated_data["rtsp_url"]:
                QMessageBox.warning(self, "Грешка", "Името и RTSP адресът не могат да бъдат празни.")
                return
            camera_to_edit.update(updated_data)
            self.refresh_cameras_view()

    def delete_camera(self):
        selected_rows = self.page_cameras.table_view.selectionModel().selectedRows()
        if not selected_rows:
            return
        row_index = selected_rows[0].row()
        camera_to_delete = self.cameras_data[row_index]
        reply = QMessageBox.question(self,
                                     "Потвърждение за изтриване",
                                     f"Сигурни ли сте, че искате да изтриете камерата '{camera_to_delete['name']}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            del self.cameras_data[row_index]
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