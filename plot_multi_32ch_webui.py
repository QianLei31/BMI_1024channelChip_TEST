import json
import queue
import socket
import struct
import threading
import time
from collections import deque
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse


CHANNELS_TOTAL = 256
BYTES_PER_POINT = 4
FRAME_BYTES = CHANNELS_TOTAL * BYTES_PER_POINT
DEFAULT_WINDOW_POINTS = 1200
DEFAULT_REFRESH_MS = 120


class StreamState:
    def __init__(self):
        self.lock = threading.Lock()
        self.raw_queue: queue.Queue = queue.Queue(maxsize=128)
        self.stop_event = threading.Event()
        self.receiver_thread = None
        self.sorter_thread = None

        self.connected = False
        self.host = "127.0.0.1"
        self.port = 10086
        self.command = "ctread"
        self.selected_channels = [i * 8 for i in range(32)]
        self.window_points = DEFAULT_WINDOW_POINTS
        self.channel_buffers = {ch: deque(maxlen=self.window_points) for ch in self.selected_channels}
        self.leftover = bytearray()

    def _ensure_buffers(self):
        self.channel_buffers = {ch: deque(maxlen=self.window_points) for ch in self.selected_channels}

    def set_channels(self, channels):
        if len(channels) != 32:
            raise ValueError("必须输入恰好32个通道")
        if len(set(channels)) != 32:
            raise ValueError("32个通道不能重复")
        if any(ch < 0 or ch >= CHANNELS_TOTAL for ch in channels):
            raise ValueError("通道号范围必须是0~255")
        with self.lock:
            self.selected_channels = list(channels)
            self._ensure_buffers()

    def set_window_points(self, window_points):
        if window_points < 200 or window_points > 8000:
            raise ValueError("窗口点数建议范围: 200~8000")
        with self.lock:
            self.window_points = int(window_points)
            self._ensure_buffers()

    def start_stream(self, host, port, command):
        self.stop_stream()
        with self.lock:
            self.host = host
            self.port = int(port)
            self.command = command
            self.stop_event.clear()
            self.leftover = bytearray()
            while not self.raw_queue.empty():
                self.raw_queue.get_nowait()

        self.receiver_thread = threading.Thread(target=self._receiver_loop, daemon=True)
        self.sorter_thread = threading.Thread(target=self._sorter_loop, daemon=True)
        self.receiver_thread.start()
        self.sorter_thread.start()

    def stop_stream(self):
        with self.lock:
            self.stop_event.set()

        for t in [self.receiver_thread, self.sorter_thread]:
            if t and t.is_alive():
                t.join(timeout=1.0)

        with self.lock:
            self.connected = False
            self.receiver_thread = None
            self.sorter_thread = None

    def _receiver_loop(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            with self.lock:
                host = self.host
                port = self.port
                command = self.command
            sock.connect((host, port))
            if command:
                sock.sendall(command.encode())
            sock.settimeout(1.0)
            with self.lock:
                self.connected = True

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
        except Exception as exc:
            print(f"[receiver] {exc}")
        finally:
            with self.lock:
                self.connected = False
            self.stop_event.set()
            sock.close()

    def _sorter_loop(self):
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

            with self.lock:
                channels = list(self.selected_channels)
                channel_buffers = self.channel_buffers

            for i in range(0, len(payload), FRAME_BYTES):
                frame = payload[i : i + FRAME_BYTES]
                for ch in channels:
                    offset = ch * BYTES_PER_POINT
                    raw = struct.unpack_from('<I', frame, offset)[0]
                    volt = raw / 4096.0 * 1.8
                    channel_buffers[ch].append(volt)

    def get_snapshot(self):
        with self.lock:
            channels = list(self.selected_channels)
            window_points = self.window_points
            connected = self.connected
            data = {str(ch): list(self.channel_buffers[ch])[-window_points:] for ch in channels}

        return {
            "connected": connected,
            "channels": channels,
            "window_points": window_points,
            "data": data,
            "ts": time.time(),
        }


STATE = StreamState()


HTML_PAGE = """<!doctype html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>32通道实时监控面板</title>
  <link href=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css\" rel=\"stylesheet\">
  <script src=\"https://cdn.jsdelivr.net/npm/chart.js\"></script>
  <style>
    body { background: #0f172a; color: #e2e8f0; }
    .glass { background: rgba(30,41,59,0.65); backdrop-filter: blur(8px); border: 1px solid rgba(148,163,184,0.2); border-radius: 14px; }
    .plot-card { height: 180px; }
    .title-gradient {
      background: linear-gradient(90deg, #38bdf8, #a78bfa 60%, #f472b6);
      -webkit-background-clip: text; background-clip: text; color: transparent;
      font-weight: 700;
    }
    .status-dot { width: 10px; height: 10px; border-radius: 999px; display:inline-block; margin-right:8px; }
    canvas { width: 100% !important; height: 138px !important; }
  </style>
</head>
<body>
<div class=\"container-fluid px-3 py-3\">
  <div class=\"d-flex justify-content-between align-items-center mb-3\">
    <h3 class=\"title-gradient m-0\">1024通道系统 · 32通道实时监控</h3>
    <div><span id=\"dot\" class=\"status-dot\" style=\"background:#ef4444\"></span><span id=\"statusText\">未连接</span></div>
  </div>

  <div class=\"glass p-3 mb-3\">
    <div class=\"row g-2 align-items-end\">
      <div class=\"col-12 col-md-2\"><label class=\"form-label\">Host</label><input id=\"host\" class=\"form-control\" value=\"127.0.0.1\"></div>
      <div class=\"col-6 col-md-1\"><label class=\"form-label\">Port</label><input id=\"port\" class=\"form-control\" value=\"10086\"></div>
      <div class=\"col-6 col-md-2\"><label class=\"form-label\">TCP命令</label><input id=\"cmd\" class=\"form-control\" value=\"ctread\"></div>
      <div class=\"col-6 col-md-2\"><label class=\"form-label\">窗口点数</label><input id=\"window\" class=\"form-control\" value=\"1200\"></div>
      <div class=\"col-6 col-md-5 d-flex gap-2\">
        <button class=\"btn btn-success\" onclick=\"startStream()\">连接并开始</button>
        <button class=\"btn btn-secondary\" onclick=\"stopStream()\">停止</button>
        <button class=\"btn btn-warning\" onclick=\"pausePlot()\">暂停</button>
        <button class=\"btn btn-info\" onclick=\"resumePlot()\">继续</button>
      </div>
    </div>
    <div class=\"mt-2\">
      <label class=\"form-label\">通道列表（32个，用逗号分隔）</label>
      <input id=\"channels\" class=\"form-control\" value=\"0,8,16,24,32,40,48,56,64,72,80,88,96,104,112,120,128,136,144,152,160,168,176,184,192,200,208,216,224,232,240,248\">
    </div>
    <div id=\"msg\" class=\"mt-2 text-warning\"></div>
  </div>

  <div id=\"grid\" class=\"row g-2\"></div>
</div>

<script>
let paused = false;
let charts = {};

function genGrid(channels){
  const grid = document.getElementById('grid');
  grid.innerHTML = '';
  charts = {};

  channels.forEach((ch) => {
    const col = document.createElement('div');
    col.className = 'col-12 col-sm-6 col-lg-3';
    const box = document.createElement('div');
    box.className = 'glass p-2 plot-card';
    const title = document.createElement('div');
    title.style.fontSize = '12px';
    title.style.marginBottom = '4px';
    title.textContent = `CH ${ch}`;

    const canvas = document.createElement('canvas');
    canvas.id = `plot-${ch}`;

    box.appendChild(title);
    box.appendChild(canvas);
    col.appendChild(box);
    grid.appendChild(col);

    const ctx = canvas.getContext('2d');
    charts[ch] = new Chart(ctx, {
      type: 'line',
      data: {
        labels: [],
        datasets: [{
          data: [],
          borderColor: '#22d3ee',
          borderWidth: 1,
          pointRadius: 0,
          fill: false,
          tension: 0,
        }],
      },
      options: {
        animation: false,
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: '#94a3b8', maxTicksLimit: 3 }, grid: { color: '#1e293b' } },
          y: { min: 0, max: 1.8, ticks: { color: '#94a3b8', maxTicksLimit: 4 }, grid: { color: '#1e293b' } },
        }
      }
    });
  });
}

function getChannels(){
  return document.getElementById('channels').value.split(',').map(s => parseInt(s.trim(),10)).filter(v => !Number.isNaN(v));
}

async function postJSON(url, obj){
  const resp = await fetch(url, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(obj)});
  return resp.json();
}

async function startStream(){
  const payload = {
    host: document.getElementById('host').value.trim(),
    port: parseInt(document.getElementById('port').value.trim(),10),
    command: document.getElementById('cmd').value,
    channels: getChannels(),
    window_points: parseInt(document.getElementById('window').value.trim(),10),
  };
  const rs = await postJSON('/api/start', payload);
  document.getElementById('msg').textContent = rs.message || '';
  if (rs.ok){ genGrid(payload.channels); }
}

async function stopStream(){
  const rs = await postJSON('/api/stop', {});
  document.getElementById('msg').textContent = rs.message || '';
}

function pausePlot(){ paused = true; document.getElementById('msg').textContent = '波形刷新已暂停'; }
function resumePlot(){ paused = false; document.getElementById('msg').textContent = '波形刷新已继续'; }

async function tick(){
  if (paused) return;
  const resp = await fetch('/api/data');
  const data = await resp.json();

  const dot = document.getElementById('dot');
  const text = document.getElementById('statusText');
  if (data.connected){ dot.style.background = '#22c55e'; text.textContent = '已连接'; }
  else { dot.style.background = '#ef4444'; text.textContent = '未连接'; }

  data.channels.forEach((ch) => {
    const key = String(ch);
    const y = data.data[key] || [];
    const labels = Array.from({length:y.length}, (_,i)=>i+1);
    const chart = charts[ch];
    if (chart){
      chart.data.labels = labels;
      chart.data.datasets[0].data = y;
      chart.update('none');
    }
  });
}

genGrid(getChannels());
setInterval(tick, %REFRESH_MS%);
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def _write_json(self, obj, status=HTTPStatus.OK):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _write_html(self, text):
        data = text.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._write_html(HTML_PAGE.replace("%REFRESH_MS%", str(DEFAULT_REFRESH_MS)))
            return
        if parsed.path == "/api/data":
            self._write_json(STATE.get_snapshot())
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self):
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length > 0 else b"{}"

        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception:
            payload = {}

        try:
            if parsed.path == "/api/start":
                channels = payload.get("channels", [])
                window_points = int(payload.get("window_points", DEFAULT_WINDOW_POINTS))
                host = payload.get("host", "127.0.0.1")
                port = int(payload.get("port", 10086))
                command = payload.get("command", "ctread")

                STATE.set_channels(channels)
                STATE.set_window_points(window_points)
                STATE.start_stream(host, port, command)
                self._write_json({"ok": True, "message": f"已连接 {host}:{port}，开始实时刷新"})
                return

            if parsed.path == "/api/stop":
                STATE.stop_stream()
                self._write_json({"ok": True, "message": "已停止TCP接收"})
                return

        except Exception as exc:
            self._write_json({"ok": False, "message": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not found")


def main():
    host = "0.0.0.0"
    port = 18080
    print(f"Web UI: http://{host}:{port}")
    server = ThreadingHTTPServer((host, port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        STATE.stop_stream()
        server.server_close()


if __name__ == "__main__":
    main()
