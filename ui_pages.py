from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableView,
    QPushButton, QLineEdit, QAbstractItemView, QHeaderView, QSpacerItem, QSizePolicy,
    QGridLayout
)
from PySide6.QtCore import Qt

class CamerasPage(QWidget):
    def __init__(self, model):
        super().__init__()
        self.model = model
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
        self.search_input.setPlaceholderText("Търсене по име или адрес...")
        
        add_button = QPushButton("Добави камера")
        add_button.setObjectName("qt_find_add_button") 
        
        self.edit_button = QPushButton("Редактирай")
        self.delete_button = QPushButton("Изтрий")
        self.scan_button = QPushButton("Сканирай мрежата")
        
        self.edit_button.setEnabled(False)
        self.delete_button.setEnabled(False)

        controls_layout.addWidget(self.search_input, 1)
        controls_layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        controls_layout.addWidget(self.scan_button)
        controls_layout.addWidget(add_button)
        controls_layout.addWidget(self.edit_button)
        controls_layout.addWidget(self.delete_button)

        self.table_view = QTableView()
        self.table_view.setModel(self.model)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table_view.verticalHeader().hide()
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setStyleSheet("QTableView { alternate-background-color: #2D2D30; background-color: #252526; }")
        
        header = self.table_view.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

        self.table_view.selectionModel().selectionChanged.connect(self.on_selection_changed)

        layout.addWidget(title)
        layout.addLayout(controls_layout)
        layout.addWidget(self.table_view)

    def on_selection_changed(self):
        is_row_selected = bool(self.table_view.selectionModel().selectedRows())
        self.edit_button.setEnabled(is_row_selected)
        self.delete_button.setEnabled(is_row_selected)

class LiveViewPage(QWidget):
    def __init__(self):
        super().__init__()
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        controls_layout = QHBoxLayout()
        controls_layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("Изглед на живо")
        font = title.font()
        font.setPointSize(18)
        font.setBold(True)
        title.setFont(font)

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

        controls_layout.addWidget(title)
        controls_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        controls_layout.addWidget(self.grid_1x1_button)
        controls_layout.addWidget(self.grid_2x2_button)
        controls_layout.addWidget(self.grid_3x3_button)
        
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(5)

        main_layout.addLayout(controls_layout)
        main_layout.addWidget(self.grid_container, 1)