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
POINTS_PER_FRAME = 4000 # 每次刷新4000个点

# --- 实时绘图相关参数 ---
PLOT_WINDOW_SIZE = POINTS_PER_FRAME # 窗口大小即为一帧的大小

# --- 通道和网络配置 ---
# *** 修改点: 定义一个包含16个通道ID的列表 ***
CHANNELS_TO_PLOT = [0, 16, 32, 48, 64, 80, 96, 112, 128, 144, 160, 176, 192, 208, 224, 240] 

HOST = '192.168.2.10'
PORT = 7
CHANNELS_TOTAL = 256
BYTES_PER_POINT = 4

# --- 线程通信 ---
RAW_DATA_QUEUE = queue.Queue(maxsize=100) 
# *** 修改点: 使用一个字典来为每个通道创建一个deque ***
SORTED_DATA_DEQUES = {ch: collections.deque() for ch in CHANNELS_TO_PLOT}
SORTED_DATA_LOCK = threading.Lock() # 仍然使用一个锁来保护整个字典
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
            data_chunk = s.recv(8192) # 适当增加缓冲区大小
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

def sorter_thread(raw_queue, sorted_deques, sorted_lock, channels_to_sort, stop_event):
    """线程2: 分拣者 - 修改为处理多个通道"""
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
            
            # *** 修改点: 遍历所有需要分拣的通道 ***
            for ch_id in channels_to_sort:
                sorted_samples = all_samples[ch_id::CHANNELS_TOTAL]
                if len(sorted_samples) > 0:
                    new_data_scaled = sorted_samples / 4096 * 1.8
                    # 使用锁来安全地更新字典中的deque
                    with sorted_lock:
                        sorted_deques[ch_id].extend(new_data_scaled)

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

def plotter_thread(sorted_deques, sorted_lock, channels_to_plot, window_size, refresh_rate_hz, stop_event):
    """线程3: 绘图者 - 修改为绘制16个子图"""
    print("绘图线程已启动...")
    
    refresh_interval_s = 1.0 / refresh_rate_hz

    try:
        plt.ion()
        # *** 修改点: 创建一个16行1列的子图网格 ***
        # sharex=True 让所有子图共享X轴，更整洁
        # figsize调整了整个窗口的尺寸，使其更高以容纳16个图
        fig, axes = plt.subplots(len(channels_to_plot), 1, figsize=(12, 24), sharex=True)
        fig.canvas.mpl_connect('close_event', on_close)
        
        # 创建一个字典来存放每个通道的line对象
        lines = {}
        x_axis = np.arange(window_size)

        # 初始化每个子图
        for i, ch_id in enumerate(channels_to_plot):
            ax = axes[i]
            line, = ax.plot(x_axis, np.zeros(window_size))
            lines[ch_id] = line
            
            ax.set_ylabel(f'Ch {ch_id}\n(V)') # Y轴标签标明通道号
            ax.grid(True)
            ax.set_ylim(0, 1.8)

        # 只在最下面的图显示X轴标签
        axes[-1].set_xlabel(f"Sample Index (Points per Frame: {window_size})")
        fig.suptitle("Real-time ADC Data (16 Channels)", fontsize=16) # 添加总标题
        fig.tight_layout(rect=[0, 0.03, 1, 0.98]) # 调整布局防止标题重叠

        while not stop_event.is_set():
            loop_start_time = time.monotonic()
            
            # *** 修改点: 遍历所有通道，检查并更新数据 ***
            with sorted_lock:
                for ch_id in channels_to_plot:
                    channel_deque = sorted_deques[ch_id]
                    if len(channel_deque) >= window_size:
                        frame_data = [channel_deque.popleft() for _ in range(window_size)]
                        # 更新对应的line对象
                        lines[ch_id].set_ydata(frame_data)
            
            # 在更新完所有可能的数据后，统一刷新一次画布
            fig.canvas.draw()
            fig.canvas.flush_events()

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
    # 检查通道列表是否为空
    if not CHANNELS_TO_PLOT:
        print("错误: CHANNELS_TO_PLOT 列表为空，请定义要监控的通道。")
    else:
        receiver = threading.Thread(target=receiver_thread, args=(HOST, PORT, RAW_DATA_QUEUE, STOP_EVENT))
        # *** 修改点: 传递新的参数给线程 ***
        sorter = threading.Thread(target=sorter_thread, args=(RAW_DATA_QUEUE, SORTED_DATA_DEQUES, SORTED_DATA_LOCK, CHANNELS_TO_PLOT, STOP_EVENT))
        plotter = threading.Thread(target=plotter_thread, args=(SORTED_DATA_DEQUES, SORTED_DATA_LOCK, CHANNELS_TO_PLOT, PLOT_WINDOW_SIZE, REFRESH_RATE_HZ, STOP_EVENT))

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