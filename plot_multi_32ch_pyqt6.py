import queue
import socket
import struct
import threading
from collections import deque

try:
    from PyQt6 import QtCore, QtGui, QtWidgets
except Exception as exc:  # noqa: BLE001
    raise SystemExit(
        "PyQt6 未安装，请先安装后再运行: pip install PyQt6\n"
        f"import error: {exc}"
    )


CHANNELS_TOTAL = 256
BYTES_PER_POINT = 4
FRAME_BYTES = CHANNELS_TOTAL * BYTES_PER_POINT
DEFAULT_CHANNELS = [i * 8 for i in range(32)]


class WaveformWidget(QtWidgets.QWidget):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self._title = title
        self._data = []
        self.setMinimumHeight(120)

    def set_title(self, title: str):
        self._title = title
        self.update()

    def set_data(self, data):
        self._data = data
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(6, 20, -6, -6)
        painter.fillRect(self.rect(), QtGui.QColor("#132238"))

        painter.setPen(QtGui.QPen(QtGui.QColor("#cbd5e1")))
        painter.drawText(8, 14, self._title)

        grid_pen = QtGui.QPen(QtGui.QColor("#233a57"))
        grid_pen.setWidth(1)
        painter.setPen(grid_pen)
        for i in range(1, 4):
            y = rect.top() + rect.height() * i / 4
            painter.drawLine(int(rect.left()), int(y), int(rect.right()), int(y))
        for i in range(1, 4):
            x = rect.left() + rect.width() * i / 4
            painter.drawLine(int(x), int(rect.top()), int(x), int(rect.bottom()))

        if not self._data:
            return

        data = self._data
        n = len(data)
        if n < 2:
            return

        wave_pen = QtGui.QPen(QtGui.QColor("#22d3ee"))
        wave_pen.setWidth(1)
        painter.setPen(wave_pen)

        points = []
        for i, v in enumerate(data):
            x = rect.left() + (i / (n - 1)) * rect.width()
            vv = max(0.0, min(1.8, float(v)))
            y = rect.bottom() - (vv / 1.8) * rect.height()
            points.append(QtCore.QPointF(x, y))
        painter.drawPolyline(points)


class TcpReceiver(threading.Thread):
    def __init__(self, host, port, cmd, raw_queue: queue.Queue, stop_event: threading.Event):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.cmd = cmd
        self.raw_queue = raw_queue
        self.stop_event = stop_event

    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((self.host, self.port))
            if self.cmd:
                sock.sendall(self.cmd.encode())
            sock.settimeout(1.0)
            while not self.stop_event.is_set():
                chunk = sock.recv(64 * 1024)
                if not chunk:
                    break
                try:
                    self.raw_queue.put(chunk, timeout=0.2)
                except queue.Full:
                    try:
                        _ = self.raw_queue.get_nowait()
                    except queue.Empty:
                        pass
                    self.raw_queue.put_nowait(chunk)
        except Exception as exc:  # noqa: BLE001
            print(f"[TcpReceiver] {exc}")
        finally:
            self.stop_event.set()
            sock.close()


class DataSorter(threading.Thread):
    def __init__(self, raw_queue: queue.Queue, state, stop_event: threading.Event):
        super().__init__(daemon=True)
        self.raw_queue = raw_queue
        self.state = state
        self.stop_event = stop_event
        self.leftover = bytearray()

    def run(self):
        while not self.stop_event.is_set():
            try:
                chunk = self.raw_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            self.leftover.extend(chunk)
            process_len = (len(self.leftover) // FRAME_BYTES) * FRAME_BYTES
            if process_len == 0:
                continue

            payload = self.leftover[:process_len]
            del self.leftover[:process_len]

            with self.state["lock"]:
                channels = list(self.state["selected_channels"])
                buffers = self.state["buffers"]

            for i in range(0, len(payload), FRAME_BYTES):
                frame = payload[i : i + FRAME_BYTES]
                for ch in channels:
                    raw = struct.unpack_from('<I', frame, ch * BYTES_PER_POINT)[0]
                    volt = raw / 4096.0 * 1.8
                    buffers[ch].append(volt)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("32通道实时监控（PyQt6）")
        self.resize(1600, 980)

        self.raw_queue: queue.Queue = queue.Queue(maxsize=128)
        self.stop_event = threading.Event()
        self.receiver = None
        self.sorter = None
        self.paused = False

        self.state = {
            "lock": threading.Lock(),
            "selected_channels": list(DEFAULT_CHANNELS),
            "buffers": {ch: deque(maxlen=1200) for ch in DEFAULT_CHANNELS},
        }

        self._build_ui()

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.refresh_plots)
        self.timer.start(100)

    def _build_ui(self):
        root = QtWidgets.QWidget()
        self.setCentralWidget(root)

        outer = QtWidgets.QVBoxLayout(root)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(8)

        control = QtWidgets.QFrame()
        control.setStyleSheet("QFrame{background:#0f1d33;border:1px solid #233a57;border-radius:12px;}")
        form = QtWidgets.QGridLayout(control)

        self.host_edit = QtWidgets.QLineEdit("127.0.0.1")
        self.port_edit = QtWidgets.QLineEdit("10086")
        self.cmd_edit = QtWidgets.QLineEdit("ctread")
        self.ch_edit = QtWidgets.QLineEdit(",".join(str(x) for x in DEFAULT_CHANNELS))

        form.addWidget(QtWidgets.QLabel("Host"), 0, 0)
        form.addWidget(self.host_edit, 0, 1)
        form.addWidget(QtWidgets.QLabel("Port"), 0, 2)
        form.addWidget(self.port_edit, 0, 3)
        form.addWidget(QtWidgets.QLabel("TCP命令"), 0, 4)
        form.addWidget(self.cmd_edit, 0, 5)

        self.btn_start = QtWidgets.QPushButton("连接并开始")
        self.btn_pause = QtWidgets.QPushButton("暂停")
        self.btn_resume = QtWidgets.QPushButton("继续")
        self.btn_apply = QtWidgets.QPushButton("应用通道")
        self.btn_stop = QtWidgets.QPushButton("停止")

        form.addWidget(self.btn_start, 0, 6)
        form.addWidget(self.btn_stop, 0, 7)
        form.addWidget(self.btn_pause, 0, 8)
        form.addWidget(self.btn_resume, 0, 9)

        form.addWidget(QtWidgets.QLabel("32通道列表（逗号分隔）"), 1, 0, 1, 2)
        form.addWidget(self.ch_edit, 1, 2, 1, 7)
        form.addWidget(self.btn_apply, 1, 9)

        self.status_label = QtWidgets.QLabel("状态：未连接")
        self.status_label.setStyleSheet("color:#22d3ee;")
        form.addWidget(self.status_label, 2, 0, 1, 10)

        outer.addWidget(control)

        grid_holder = QtWidgets.QWidget()
        grid = QtWidgets.QGridLayout(grid_holder)
        grid.setSpacing(8)
        self.wave_widgets = []
        for i in range(32):
            w = WaveformWidget(f"CH {DEFAULT_CHANNELS[i]}")
            self.wave_widgets.append(w)
            grid.addWidget(w, i // 4, i % 4)
        outer.addWidget(grid_holder, 1)

        self.setStyleSheet(
            """
            QMainWindow { background:#0b1528; color:#e2e8f0; }
            QLabel { color:#cbd5e1; }
            QLineEdit { background:#0f172a; color:#e2e8f0; border:1px solid #334155; border-radius:6px; padding:4px; }
            QPushButton { background:#1d4ed8; color:#e2e8f0; border:none; border-radius:6px; padding:6px 10px; }
            QPushButton:hover { background:#2563eb; }
            """
        )

        self.btn_start.clicked.connect(self.start_stream)
        self.btn_stop.clicked.connect(self.stop_stream)
        self.btn_pause.clicked.connect(self.pause)
        self.btn_resume.clicked.connect(self.resume)
        self.btn_apply.clicked.connect(self.apply_channels)

    def parse_channels(self):
        try:
            channels = [int(x.strip()) for x in self.ch_edit.text().split(",") if x.strip()]
        except ValueError as exc:
            raise ValueError("通道必须是整数") from exc

        if len(channels) != 32:
            raise ValueError("必须输入32个通道")
        if len(set(channels)) != 32:
            raise ValueError("通道不能重复")
        if any(ch < 0 or ch >= CHANNELS_TOTAL for ch in channels):
            raise ValueError("通道范围必须是0~255")
        return channels

    def apply_channels(self):
        try:
            channels = self.parse_channels()
        except ValueError as exc:
            QtWidgets.QMessageBox.warning(self, "通道设置错误", str(exc))
            return False

        with self.state["lock"]:
            self.state["selected_channels"] = channels
            self.state["buffers"] = {ch: deque(maxlen=1200) for ch in channels}

        for i, ch in enumerate(channels):
            self.wave_widgets[i].set_title(f"CH {ch}")

        self.status_label.setText("状态：通道已更新")
        return True

    def start_stream(self):
        self.stop_stream()
        if not self.apply_channels():
            return

        host = self.host_edit.text().strip()
        cmd = self.cmd_edit.text().strip()
        try:
            port = int(self.port_edit.text().strip())
        except ValueError:
            QtWidgets.QMessageBox.warning(self, "端口错误", "Port 必须为整数")
            return

        self.stop_event = threading.Event()
        while not self.raw_queue.empty():
            self.raw_queue.get_nowait()

        self.receiver = TcpReceiver(host, port, cmd, self.raw_queue, self.stop_event)
        self.sorter = DataSorter(self.raw_queue, self.state, self.stop_event)
        self.receiver.start()
        self.sorter.start()
        self.status_label.setText(f"状态：已连接 {host}:{port}")

    def stop_stream(self):
        if self.stop_event:
            self.stop_event.set()
        for t in [self.receiver, self.sorter]:
            if t and t.is_alive():
                t.join(timeout=1.0)
        self.receiver = None
        self.sorter = None
        self.status_label.setText("状态：已停止")

    def pause(self):
        self.paused = True
        self.status_label.setText("状态：波形已暂停")

    def resume(self):
        self.paused = False
        self.status_label.setText("状态：实时更新中")

    def refresh_plots(self):
        if self.paused:
            return

        with self.state["lock"]:
            channels = list(self.state["selected_channels"])
            buffers = self.state["buffers"]

        for i, ch in enumerate(channels):
            self.wave_widgets[i].set_data(list(buffers[ch]))

    def closeEvent(self, event):
        self.stop_stream()
        event.accept()


def main():
    app = QtWidgets.QApplication([])
    win = MainWindow()
    win.show()
    app.exec()


if __name__ == "__main__":
    main()
