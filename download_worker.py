from PySide6.QtCore import QObject, Signal
import requests

class DownloadWorker(QObject):
    """
    Worker, който работи в отделна нишка и управлява изтеглянето на файл.
    """
    finished = Signal(str)  # Изпраща пътя до сваления файл при успех
    error = Signal(str)     # Изпраща съобщение за грешка
    progress = Signal(int)  # Изпраща прогреса в проценти

    def __init__(self, remote_client, remote_path, local_path):
        super().__init__()
        self.remote_client = remote_client
        self.remote_path = remote_path
        self.local_path = local_path
        self._is_cancelled = False

    def run(self):
        """Стартира процеса по изтегляне."""
        try:
            success = self.remote_client.download_file_with_progress(
                self.remote_path, 
                self.local_path, 
                self.progress.emit,
                lambda: self._is_cancelled
            )
            
            if self._is_cancelled:
                self.error.emit("Изтеглянето е прекратено.")
            elif success:
                self.finished.emit(self.local_path)
            else:
                self.error.emit("Неуспешно изтегляне на файла.")

        except Exception as e:
            self.error.emit(f"Грешка: {e}")

    def cancel(self):
        self._is_cancelled = True