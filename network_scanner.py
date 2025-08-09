import socket
from ipaddress import ip_network
from PySide6.QtCore import QObject, Signal

class NetworkScanner(QObject):
    camera_found = Signal(str)
    scan_progress = Signal(int)
    scan_finished = Signal(str)

    def __init__(self, subnet):
        super().__init__()
        self.subnet = subnet
        self._is_cancelled = False

    def run(self):
        try:
            hosts = list(self.subnet.hosts())
            total_hosts = len(hosts)
            for i, ip in enumerate(hosts):
                if self._is_cancelled:
                    break
                ip_str = str(ip)
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(0.1)
                    if sock.connect_ex((ip_str, 554)) == 0:
                        self.camera_found.emit(ip_str)
                
                progress = int(((i + 1) / total_hosts) * 100)
                self.scan_progress.emit(progress)

            message = "Сканирането е прекратено." if self._is_cancelled else "Сканирането на мрежата приключи."
            self.scan_finished.emit(message)
        except Exception as e:
            self.scan_finished.emit(f"Грешка при сканиране: {e}")

    def cancel(self):
        self._is_cancelled = True

def get_local_subnet():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        return ip_network(f"{ip}/24", strict=False)
    except Exception:
        return None