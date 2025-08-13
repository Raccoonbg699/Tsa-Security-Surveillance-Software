from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QSpacerItem, QSizePolicy,
    QGridLayout, QComboBox, QListWidget, QFormLayout, QFileDialog
)
from PySide6.QtCore import Qt

from data_manager import get_translator

class CamerasPage(QWidget):
    """Страница за управление на камери."""
    def __init__(self):
        super().__init__()
        translator = get_translator()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        title = QLabel(translator.get_string("page_cameras_title"))
        font = title.font()
        font.setPointSize(18)
        font.setBold(True)
        title.setFont(font)
        controls_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(translator.get_string("search_placeholder"))
        self.add_button = QPushButton(translator.get_string("add_button"))
        self.edit_button = QPushButton(translator.get_string("edit_button"))
        self.delete_button = QPushButton(translator.get_string("delete_button"))
        self.scan_button = QPushButton(translator.get_string("scan_button"))
        self.edit_button.setEnabled(False)
        self.delete_button.setEnabled(False)
        controls_layout.addWidget(self.search_input, 1)
        controls_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        controls_layout.addWidget(self.scan_button)
        controls_layout.addWidget(self.add_button)
        controls_layout.addWidget(self.edit_button)
        controls_layout.addWidget(self.delete_button)
        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.itemSelectionChanged.connect(self.on_selection_changed)
        layout.addWidget(title)
        layout.addLayout(controls_layout)
        layout.addWidget(self.list_widget)

    def on_selection_changed(self):
        is_selected = bool(self.list_widget.selectedItems())
        self.edit_button.setEnabled(is_selected)
        self.delete_button.setEnabled(is_selected)

class LiveViewPage(QWidget):
    """Страница за изглед на живо."""
    def __init__(self):
        super().__init__()
        translator = get_translator()
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        title = QLabel(translator.get_string("page_live_view_title"))
        font = title.font()
        font.setPointSize(18)
        font.setBold(True)
        title.setFont(font)
        self.camera_selector = QComboBox()
        self.camera_selector.setMinimumWidth(200)
        self.camera_selector.hide()
        self.grid_1x1_button = QPushButton("1x1")
        self.grid_2x2_button = QPushButton("2x2")
        self.grid_3x3_button = QPushButton("3x3")
        self.grid_1x1_button.setCheckable(True)
        self.grid_2x2_button.setCheckable(True)
        self.grid_3x3_button.setCheckable(True)
        self.grid_1x1_button.setAutoExclusive(True)
        self.grid_2x2_button.setAutoExclusive(True)
        self.grid_3x3_button.setAutoExclusive(True)
        self.grid_2x2_button.setChecked(True)
        top_layout.addWidget(title)
        top_layout.addWidget(self.camera_selector)
        top_layout.addStretch()
        top_layout.addWidget(self.grid_1x1_button)
        top_layout.addWidget(self.grid_2x2_button)
        top_layout.addWidget(self.grid_3x3_button)
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(5)
        bottom_controls = QHBoxLayout()
        self.snapshot_button = QPushButton(translator.get_string("snapshot_button"))
        self.record_button = QPushButton(translator.get_string("record_button"))
        self.record_button.setCheckable(True)
        bottom_controls.addStretch()
        bottom_controls.addWidget(self.snapshot_button)
        bottom_controls.addWidget(self.record_button)
        main_layout.addLayout(top_layout)
        main_layout.addWidget(self.grid_container, 1)
        main_layout.addLayout(bottom_controls)

class RecordingsPage(QWidget):
    """Страница за преглед на записи."""
    def __init__(self):
        super().__init__()
        translator = get_translator()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        top_layout = QHBoxLayout()
        title = QLabel(translator.get_string("page_recordings_title"))
        font = title.font()
        font.setPointSize(18)
        font.setBold(True)
        title.setFont(font)
        self.view_in_app_button = QPushButton("Преглед в програмата")
        self.open_in_player_button = QPushButton("Отваряне в плейър")
        self.delete_button = QPushButton(translator.get_string("delete_recording_button"))
        self.view_in_app_button.setEnabled(False)
        self.open_in_player_button.setEnabled(False)
        self.delete_button.setEnabled(False)
        top_layout.addWidget(title)
        top_layout.addStretch()
        top_layout.addWidget(self.view_in_app_button)
        top_layout.addWidget(self.open_in_player_button)
        top_layout.addWidget(self.delete_button)
        filters_layout = QHBoxLayout()
        filters_layout.addWidget(QLabel(translator.get_string("filters_label")))
        self.camera_filter = QComboBox()
        self.event_type_filter = QComboBox()
        filters_layout.addWidget(self.camera_filter)
        filters_layout.addWidget(self.event_type_filter)
        filters_layout.addStretch()
        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.itemSelectionChanged.connect(self.on_selection_changed)
        layout.addLayout(top_layout)
        layout.addLayout(filters_layout)
        layout.addWidget(self.list_widget)
        
    def on_selection_changed(self):
        is_selected = bool(self.list_widget.selectedItems())
        self.view_in_app_button.setEnabled(is_selected)
        self.open_in_player_button.setEnabled(is_selected)
        self.delete_button.setEnabled(is_selected)

class SettingsPage(QWidget):
    """Страница за настройки на приложението."""
    def __init__(self):
        super().__init__()
        translator = get_translator()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        title = QLabel(translator.get_string("page_settings_title"))
        font = title.font()
        font.setPointSize(18)
        font.setBold(True)
        title.setFont(font)

        form_layout = QFormLayout()
        form_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form_layout.setSpacing(15)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems([translator.get_string("dark_theme"), translator.get_string("light_theme")])
        
        self.grid_combo = QComboBox()
        self.grid_combo.addItems(["1x1", "2x2", "3x3"])
        
        self.lang_combo = QComboBox()
        self.lang_combo.addItem("Български", "bg")
        self.lang_combo.addItem("English", "en")

        self.recording_structure_combo = QComboBox()
        self.recording_structure_combo.addItem(translator.get_string("single_folder_option"), "single")
        self.recording_structure_combo.addItem(translator.get_string("per_camera_folder_option"), "per_camera")

        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        browse_button = QPushButton("...")
        browse_button.setFixedWidth(40)
        browse_button.clicked.connect(self.select_recording_path)
        path_layout.addWidget(self.path_edit, 1)
        path_layout.addWidget(browse_button)

        form_layout.addRow(translator.get_string("app_theme_label"), self.theme_combo)
        form_layout.addRow(translator.get_string("default_view_label"), self.grid_combo)
        form_layout.addRow(translator.get_string("language_label"), self.lang_combo)
        form_layout.addRow(translator.get_string("recordings_folder_label"), path_layout)
        form_layout.addRow(translator.get_string("recording_structure_label"), self.recording_structure_combo)
        
        self.save_button = QPushButton(translator.get_string("save_changes_button"))
        self.save_button.setObjectName("AccentButton")

        layout.addWidget(title)
        layout.addLayout(form_layout)
        layout.addStretch()
        layout.addWidget(self.save_button, 0, Qt.AlignmentFlag.AlignRight)

    def select_recording_path(self):
        directory = QFileDialog.getExistingDirectory(self, "Изберете папка за записи")
        if directory:
            self.path_edit.setText(directory)

class UsersPage(QWidget):
    """Страница за управление на потребители."""
    def __init__(self):
        super().__init__()
        translator = get_translator()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        title = QLabel(translator.get_string("page_users_title"))
        font = title.font()
        font.setPointSize(18)
        font.setBold(True)
        title.setFont(font)
        buttons_layout = QHBoxLayout()
        self.add_button = QPushButton(translator.get_string("add_user_button"))
        self.edit_button = QPushButton(translator.get_string("edit_button"))
        self.delete_button = QPushButton(translator.get_string("delete_button"))
        self.edit_button.setEnabled(False)
        self.delete_button.setEnabled(False)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.add_button)
        buttons_layout.addWidget(self.edit_button)
        buttons_layout.addWidget(self.delete_button)
        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.itemSelectionChanged.connect(self.on_selection_changed)
        layout.addWidget(title)
        layout.addLayout(buttons_layout)
        layout.addWidget(self.list_widget)

    def on_selection_changed(self):
        is_selected = bool(self.list_widget.selectedItems())
        self.edit_button.setEnabled(is_selected)
        self.delete_button.setEnabled(is_selected)