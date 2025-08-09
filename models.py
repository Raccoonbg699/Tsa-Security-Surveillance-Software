from PySide6.QtCore import QAbstractTableModel, Qt

class CameraTableModel(QAbstractTableModel):
    def __init__(self, data=None):
        super().__init__()
        self._data = data or []
        self.headers = ["Име на камера", "RTSP Адрес", "Статус"]

    def data(self, index, role):
        if role == Qt.ItemDataRole.DisplayRole:
            row_data = self._data[index.row()]
            col = index.column()
            if col == 0:
                return row_data.get("name")
            if col == 1:
                return row_data.get("rtsp_url")
            if col == 2:
                return "Активна" if row_data.get("is_active") else "Неактивна"
        return None

    def rowCount(self, index):
        return len(self._data)

    def columnCount(self, index):
        return len(self.headers)

    def headerData(self, section, orientation, role):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self.headers[section]
        return None
    
    def update_data(self, new_data):
        self.beginResetModel()
        self._data = new_data
        self.endResetModel()