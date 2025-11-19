import socket
import matplotlib.pyplot as plt
import numpy as np
import time
import collections
import threading
import queue

##########################################  USER DEFINE  ###################################

# --- 刷新率和数据帧大小 ---
REFRESH_RATE_HZ = 5  # 每秒刷新5次
POINTS_PER_FRAME = 4000 # 每次刷新4000个点 (20k / 5)

# --- 实时绘图相关参数 ---
PLOT_WINDOW_SIZE = POINTS_PER_FRAME # 窗口大小即为一帧的大小

# --- 通道和网络配置 ---
CHANNEL_TO_PLOT = 239
HOST = '192.168.2.10'
PORT = 7
CHANNELS_TOTAL = 256
BYTES_PER_POINT = 4

# --- 线程通信 ---
# 接收者 -> 分拣者
RAW_DATA_QUEUE = queue.Queue(maxsize=100) 
# 分拣者 -> 绘图者 (改用线程安全的deque)
SORTED_DATA_DEQUE = collections.deque()
SORTED_DATA_LOCK = threading.Lock()
# 全局停止信号
STOP_EVENT = threading.Event()

###########################################  DEFINE END   ########################################

def receiver_thread(host, port, raw_queue, stop_event):
    """线程1: 接收者 - 保持不变"""
    print("接收线程已启动...")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((host, port))
        s.sendall("ctread".encode())
        print("接收线程：连接成功。")
        while not stop_event.is_set():
            data_chunk = s.recv(4096)
            if not data_chunk:
                print("接收线程：连接已断开。")
                break
            raw_queue.put(data_chunk)
    except Exception as e:
        print(f"接收线程错误: {e}")
    finally:
        print("接收线程正在关闭...")
        s.close()
        stop_event.set()

def sorter_thread(raw_queue, sorted_deque, sorted_lock, channel_to_sort, stop_event):
    """线程2: 分拣者 - 修改为向deque写入数据"""
    print("分拣线程已启动...")
    incomplete_chunk = b''
    while not stop_event.is_set():
        try:
            raw_chunk = raw_queue.get(timeout=1)
            full_data = incomplete_chunk + raw_chunk
            total_bytes = len(full_data)
            bytes_to_process = total_bytes - (total_bytes % (CHANNELS_TOTAL * BYTES_PER_POINT))
            
            if bytes_to_process == 0:
                incomplete_chunk = full_data
                continue

            data_to_process = full_data[:bytes_to_process]
            incomplete_chunk = full_data[bytes_to_process:]

            all_samples = np.frombuffer(data_to_process, dtype=np.int32)
            sorted_samples = all_samples[channel_to_sort::CHANNELS_TOTAL]
            
            # 将数据转换为电压值
            new_data_scaled = sorted_samples / 4096 * 1.8

            if len(new_data_scaled) > 0:
                # 使用锁来安全地向共享deque添加数据
                with sorted_lock:
                    sorted_deque.extend(new_data_scaled)

        except queue.Empty:
            continue
        except Exception as e:
            print(f"分拣线程错误: {e}")
            stop_event.set()
            break
    print("分拣线程已关闭。")

def on_close(event):
    """当matplotlib窗口被关闭时，这个函数会被调用"""
    print("检测到绘图窗口关闭，正在通知所有线程停止...")
    STOP_EVENT.set()

def plotter_thread(sorted_deque, sorted_lock, window_size, refresh_rate_hz, stop_event):
    """线程3: 绘图者 - 完全重写为时间驱动模式"""
    print("绘图线程已启动...")
    
    refresh_interval_s = 1.0 / refresh_rate_hz # 计算刷新周期

    try:
        plt.ion()
        fig, ax = plt.subplots(figsize=(12, 6))
        fig.canvas.mpl_connect('close_event', on_close)
        
        # X轴是固定的0到3999
        x_axis = np.arange(window_size)
        # 初始Y轴数据为全零
        line, = ax.plot(x_axis, np.zeros(window_size))
        
        ax.set_title(f"Real-time ADC Data (Channel {CHANNEL_TO_PLOT}) - {refresh_rate_hz} Hz Refresh")
        ax.set_xlabel(f"Sample Index (Points per Frame: {window_size})")
        ax.set_ylabel("Amplitude / V")
        ax.grid(True)
        ax.set_ylim(0, 1.8) # 固定Y轴以防跳动
        
        while not stop_event.is_set():
            loop_start_time = time.monotonic()
            
            frame_data = None
            
            # --- 从共享deque中提取一帧数据 ---
            with sorted_lock:
                if len(sorted_deque) >= window_size:
                    # 如果数据充足，从左边提取一整帧
                    frame_data = [sorted_deque.popleft() for _ in range(window_size)]

            # --- 更新绘图 ---
            if frame_data is not None:
                # 只有在成功提取到一帧数据时才更新
                line.set_ydata(frame_data)
                fig.canvas.draw()
                fig.canvas.flush_events()
            else:
                # 如果数据不够，可以选择不刷新，或者显示提示
                # 这里我们简单地跳过刷新，等待数据积累
                # 仍然需要flush_events来保持窗口响应
                fig.canvas.flush_events()

            # --- 精确控制刷新频率 ---
            elapsed_time = time.monotonic() - loop_start_time
            sleep_time = refresh_interval_s - elapsed_time
            if sleep_time > 0:
                time.sleep(sleep_time)

    except Exception as e:
        if "application has been destroyed" not in str(e):
             print(f"绘图线程错误: {e}")
    finally:
        print("绘图线程已关闭。")
        stop_event.set()


if __name__ == "__main__":
    receiver = threading.Thread(target=receiver_thread, args=(HOST, PORT, RAW_DATA_QUEUE, STOP_EVENT))
    sorter = threading.Thread(target=sorter_thread, args=(RAW_DATA_QUEUE, SORTED_DATA_DEQUE, SORTED_DATA_LOCK, CHANNEL_TO_PLOT, STOP_EVENT))
    plotter = threading.Thread(target=plotter_thread, args=(SORTED_DATA_DEQUE, SORTED_DATA_LOCK, PLOT_WINDOW_SIZE, REFRESH_RATE_HZ, STOP_EVENT))

    receiver.start()
    sorter.start()
    plotter.start()

    try:
        while plotter.is_alive():
            plotter.join(0.5)
    except KeyboardInterrupt:
        print("\n检测到用户中断 (Ctrl+C)，正在通知所有线程停止...")
        STOP_EVENT.set()

    receiver.join()
    sorter.join()
    plotter.join()
    
    print("所有线程已安全退出，程序结束。")