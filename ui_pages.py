from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QSpacerItem, QSizePolicy,
    QGridLayout, QComboBox, QListWidget, QFormLayout, QFileDialog
)
from PySide6.QtCore import Qt

class CamerasPage(QWidget):
    """Страница за управление на камери."""
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = QLabel("Управление на камери")
        font = title.font()
        font.setPointSize(18)
        font.setBold(True)
        title.setFont(font)

        controls_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Търсене...")
        
        self.add_button = QPushButton("Добави")
        self.edit_button = QPushButton("Редактирай")
        self.delete_button = QPushButton("Изтрий")
        self.scan_button = QPushButton("Сканирай")
        
        self.edit_button.setEnabled(False)
        self.delete_button.setEnabled(False)

        controls_layout.addWidget(self.search_input, 1)
        controls_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        controls_layout.addWidget(self.scan_button)
        controls_layout.addWidget(self.add_button)
        controls_layout.addWidget(self.edit_button)
        controls_layout.addWidget(self.delete_button)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("QListWidget::item { padding: 8px; }")
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
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("Изглед на живо")
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
        self.snapshot_button = QPushButton("Снимка")
        self.record_button = QPushButton("Запис")
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
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        top_layout = QHBoxLayout()
        title = QLabel("Преглед на записи")
        font = title.font()
        font.setPointSize(18)
        font.setBold(True)
        title.setFont(font)
        
        self.view_button = QPushButton("Преглед на запис")
        self.delete_button = QPushButton("Изтрий запис")
        self.view_button.setEnabled(False)
        self.delete_button.setEnabled(False)

        top_layout.addWidget(title)
        top_layout.addStretch()
        top_layout.addWidget(self.view_button)
        top_layout.addWidget(self.delete_button)

        filters_layout = QHBoxLayout()
        filters_layout.addWidget(QLabel("Филтри:"))
        self.camera_filter = QComboBox()
        self.event_type_filter = QComboBox()
        filters_layout.addWidget(self.camera_filter)
        filters_layout.addWidget(self.event_type_filter)
        filters_layout.addStretch()

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("QListWidget::item { padding: 8px; }")
        self.list_widget.setAlternatingRowColors(True)
        
        self.list_widget.itemSelectionChanged.connect(self.on_selection_changed)

        layout.addLayout(top_layout)
        layout.addLayout(filters_layout)
        layout.addWidget(self.list_widget)
        
    def on_selection_changed(self):
        is_selected = bool(self.list_widget.selectedItems())
        self.view_button.setEnabled(is_selected)
        self.delete_button.setEnabled(is_selected)

class SettingsPage(QWidget):
    """Страница за настройки на приложението."""
    def __init__(self):
        super().__init__()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        title = QLabel("Настройки")
        font = title.font()
        font.setPointSize(18)
        font.setBold(True)
        title.setFont(font)

        form_layout = QFormLayout()
        form_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form_layout.setSpacing(15)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Тъмна", "Светла"])
        
        self.grid_combo = QComboBox()
        self.grid_combo.addItems(["1x1", "2x2", "3x3"])

        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        browse_button = QPushButton("...")
        browse_button.setFixedWidth(40)
        browse_button.clicked.connect(self.select_recording_path)
        path_layout.addWidget(self.path_edit, 1)
        path_layout.addWidget(browse_button)

        form_layout.addRow("Тема на приложението:", self.theme_combo)
        form_layout.addRow("Изглед по подразбиране:", self.grid_combo)
        form_layout.addRow("Папка за записи:", path_layout)
        
        self.save_button = QPushButton("Запази промените")
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
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = QLabel("Управление на потребители")
        font = title.font()
        font.setPointSize(18)
        font.setBold(True)
        title.setFont(font)

        buttons_layout = QHBoxLayout()
        self.add_button = QPushButton("Добави потребител")
        self.edit_button = QPushButton("Редактирай")
        self.delete_button = QPushButton("Изтрий")
        self.edit_button.setEnabled(False)
        self.delete_button.setEnabled(False)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.add_button)
        buttons_layout.addWidget(self.edit_button)
        buttons_layout.addWidget(self.delete_button)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("QListWidget::item { padding: 8px; }")
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.itemSelectionChanged.connect(self.on_selection_changed)

        layout.addWidget(title)
        layout.addLayout(buttons_layout)
        layout.addWidget(self.list_widget)

    def on_selection_changed(self):
        is_selected = bool(self.list_widget.selectedItems())
        self.edit_button.setEnabled(is_selected)
        self.delete_button.setEnabled(is_selected)