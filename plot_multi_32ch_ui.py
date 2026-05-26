import queue
import socket
import threading
from collections import deque
import tkinter as tk
from tkinter import ttk, messagebox

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


CHANNELS_TOTAL = 256
BYTES_PER_POINT = 4
FRAME_BYTES = CHANNELS_TOTAL * BYTES_PER_POINT
class BufferPool:
    """Simple fixed-size bytearray pool to reduce repeated allocation."""

    def __init__(self, buffer_size: int, pool_size: int = 64):
        self._buffer_size = buffer_size
        self._queue: "queue.Queue[bytearray]" = queue.Queue(maxsize=pool_size)
        for _ in range(pool_size):
            self._queue.put(bytearray(buffer_size))

    def acquire(self, timeout: float = 0.1) -> bytearray:
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return bytearray(self._buffer_size)

    def release(self, buf: bytearray) -> None:
        if len(buf) != self._buffer_size:
            return
        try:
            self._queue.put_nowait(buf)
        except queue.Full:
            pass


class TcpReceiver(threading.Thread):
    def __init__(
        self,
        host: str,
        port: int,
        command: str,
        raw_queue: queue.Queue,
        buffer_pool: BufferPool,
        stop_event: threading.Event,
    ):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.command = command
        self.raw_queue = raw_queue
        self.buffer_pool = buffer_pool
        self.stop_event = stop_event

    def run(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((self.host, self.port))
            if self.command:
                sock.sendall(self.command.encode())
            sock.settimeout(1.0)
            while not self.stop_event.is_set():
                buf = self.buffer_pool.acquire()
                view = memoryview(buf)
                recv_n = sock.recv_into(view)
                if recv_n <= 0:
                    self.buffer_pool.release(buf)
                    break
                try:
                    self.raw_queue.put((buf, recv_n), timeout=0.5)
                except queue.Full:
                    # If parse side is temporarily slow, drop oldest to keep RT.
                    old_buf, _ = self.raw_queue.get_nowait()
                    self.buffer_pool.release(old_buf)
                    self.raw_queue.put_nowait((buf, recv_n))
        except Exception as exc:
            print(f"[TcpReceiver] {exc}")
        finally:
            self.stop_event.set()
            sock.close()


class DataSorter(threading.Thread):
    def __init__(
        self,
        raw_queue: queue.Queue,
        selected_channels_getter,
        channel_buffers,
        channel_lock: threading.Lock,
        stop_event: threading.Event,
    ):
        super().__init__(daemon=True)
        self.raw_queue = raw_queue
        self.selected_channels_getter = selected_channels_getter
        self.channel_buffers = channel_buffers
        self.channel_lock = channel_lock
        self.stop_event = stop_event
        self.leftover = bytearray()
        self.buffer_pool = None

    def set_buffer_pool(self, buffer_pool: BufferPool):
        self.buffer_pool = buffer_pool

    def run(self):
        while not self.stop_event.is_set():
            try:
                buf, recv_n = self.raw_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            chunk = bytes(memoryview(buf)[:recv_n])
            if self.buffer_pool is not None:
                self.buffer_pool.release(buf)

            self.leftover.extend(chunk)
            process_len = (len(self.leftover) // FRAME_BYTES) * FRAME_BYTES
            if process_len == 0:
                continue

            payload = self.leftover[:process_len]
            del self.leftover[:process_len]

            samples = np.frombuffer(payload, dtype='<u4').reshape(-1, CHANNELS_TOTAL)
            selected = self.selected_channels_getter()
            if not selected:
                continue

            with self.channel_lock:
                for ch in selected:
                    if ch not in self.channel_buffers:
                        continue
                    volts = samples[:, ch].astype(np.float32) / 4096.0 * 1.8
                    self.channel_buffers[ch].extend(volts.tolist())


class Plot32ChUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("32-Channel Real-Time Monitor (TCP)")

        self.raw_queue: queue.Queue = queue.Queue(maxsize=128)
        self.buffer_pool = BufferPool(buffer_size=64 * 1024, pool_size=128)
        self.channel_lock = threading.Lock()
        self.stop_event = threading.Event()
        self.paused = False

        self.selected_channels = self._default_channels()
        self.window_points = 800
        self.channel_buffers = {ch: deque(maxlen=self.window_points) for ch in self.selected_channels}

        self.receiver_thread = None
        self.sorter_thread = None

        self._build_controls()
        self._build_plot()
        self._schedule_plot_update()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    @staticmethod
    def _default_channels():
        return [i * 8 for i in range(32)]

    def _build_controls(self):
        frame = ttk.Frame(self.root, padding=8)
        frame.pack(fill=tk.X)

        ttk.Label(frame, text="Host").grid(row=0, column=0, sticky=tk.W)
        self.host_var = tk.StringVar(value="127.0.0.1")
        ttk.Entry(frame, textvariable=self.host_var, width=14).grid(row=0, column=1, padx=4)

        ttk.Label(frame, text="Port").grid(row=0, column=2, sticky=tk.W)
        self.port_var = tk.StringVar(value="10086")
        ttk.Entry(frame, textvariable=self.port_var, width=8).grid(row=0, column=3, padx=4)

        ttk.Label(frame, text="TCP Cmd").grid(row=0, column=4, sticky=tk.W)
        self.cmd_var = tk.StringVar(value="ctread")
        ttk.Entry(frame, textvariable=self.cmd_var, width=10).grid(row=0, column=5, padx=4)

        ttk.Label(frame, text="Channels (32 ids, comma-separated)").grid(row=1, column=0, columnspan=3, sticky=tk.W)
        self.channels_var = tk.StringVar(value=",".join(map(str, self.selected_channels)))
        ttk.Entry(frame, textvariable=self.channels_var, width=70).grid(row=1, column=3, columnspan=5, sticky=tk.EW, padx=4, pady=4)

        self.connect_btn = ttk.Button(frame, text="连接并开始", command=self.start_stream)
        self.connect_btn.grid(row=0, column=6, padx=4)

        ttk.Button(frame, text="应用通道", command=self.apply_channels).grid(row=0, column=7, padx=4)
        ttk.Button(frame, text="暂停", command=self.pause).grid(row=2, column=6, pady=4)
        ttk.Button(frame, text="继续", command=self.resume).grid(row=2, column=7, pady=4)

        self.status_var = tk.StringVar(value="状态: 未连接")
        ttk.Label(frame, textvariable=self.status_var).grid(row=2, column=0, columnspan=6, sticky=tk.W)

    def _build_plot(self):
        fig = Figure(figsize=(14, 10), dpi=100)
        self.axes = []
        self.lines = {}
        x = np.arange(self.window_points)

        for idx in range(32):
            ax = fig.add_subplot(8, 4, idx + 1)
            ch = self.selected_channels[idx]
            line, = ax.plot(x, np.zeros(self.window_points, dtype=np.float32), lw=0.8)
            ax.set_title(f"CH {ch}", fontsize=8)
            ax.set_ylim(0, 1.8)
            ax.set_xticks([])
            ax.set_yticks([0.0, 0.9, 1.8])
            self.axes.append(ax)
            self.lines[ch] = line

        fig.tight_layout()
        self.fig = fig
        self.canvas = FigureCanvasTkAgg(fig, master=self.root)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def parse_channels(self):
        try:
            channels = [int(x.strip()) for x in self.channels_var.get().split(',') if x.strip() != ""]
        except ValueError:
            raise ValueError("通道列表必须是整数")

        if len(channels) != 32:
            raise ValueError("必须恰好填写32个通道")
        if any(ch < 0 or ch >= CHANNELS_TOTAL for ch in channels):
            raise ValueError("通道号必须在0~255")
        if len(set(channels)) != 32:
            raise ValueError("通道号不能重复")
        return channels

    def apply_channels(self):
        try:
            new_channels = self.parse_channels()
        except ValueError as exc:
            messagebox.showerror("通道设置错误", str(exc))
            return

        with self.channel_lock:
            self.selected_channels = new_channels
            self.channel_buffers = {ch: deque(maxlen=self.window_points) for ch in self.selected_channels}
            for idx, ax in enumerate(self.axes):
                ch = self.selected_channels[idx]
                self.lines[ch] = ax.lines[0]
                ax.set_title(f"CH {ch}", fontsize=8)

        self.status_var.set("状态: 通道已更新")

    def get_selected_channels(self):
        with self.channel_lock:
            return list(self.selected_channels)

    def start_stream(self):
        if self.receiver_thread and self.receiver_thread.is_alive():
            messagebox.showinfo("提示", "TCP已在运行")
            return

        try:
            port = int(self.port_var.get())
            self.apply_channels()
        except Exception:
            return

        self.stop_event.clear()
        while not self.raw_queue.empty():
            old_buf, _ = self.raw_queue.get_nowait()
            self.buffer_pool.release(old_buf)

        self.receiver_thread = TcpReceiver(
            self.host_var.get().strip(),
            port,
            self.cmd_var.get().strip(),
            self.raw_queue,
            self.buffer_pool,
            self.stop_event,
        )
        self.sorter_thread = DataSorter(
            self.raw_queue,
            self.get_selected_channels,
            self.channel_buffers,
            self.channel_lock,
            self.stop_event,
        )
        self.sorter_thread.set_buffer_pool(self.buffer_pool)

        self.receiver_thread.start()
        self.sorter_thread.start()
        self.status_var.set("状态: TCP接收中")

    def pause(self):
        self.paused = True
        self.status_var.set("状态: 已暂停")

    def resume(self):
        self.paused = False
        self.status_var.set("状态: 实时更新中")

    def _schedule_plot_update(self):
        self.update_plot()
        self.root.after(100, self._schedule_plot_update)

    def update_plot(self):
        if self.paused:
            return

        with self.channel_lock:
            for idx, ch in enumerate(self.selected_channels):
                data = self.channel_buffers.get(ch)
                if data is None:
                    continue
                y = np.zeros(self.window_points, dtype=np.float32)
                arr = np.array(data, dtype=np.float32)
                if arr.size > 0:
                    y[-arr.size:] = arr[-self.window_points :]
                line = self.axes[idx].lines[0]
                line.set_ydata(y)

        self.canvas.draw_idle()

    def on_close(self):
        self.stop_event.set()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = Plot32ChUI(root)
    root.geometry("1500x900")
    root.mainloop()


if __name__ == "__main__":
    main()
