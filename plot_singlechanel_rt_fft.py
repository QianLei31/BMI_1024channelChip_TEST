import socket
import matplotlib.pyplot as plt
from matplotlib.offsetbox import AnchoredText
import numpy as np
import time
import collections
import threading
import queue

# 假设您的cal_sndr函数在一个名为 fun_cal_sndr.py 的文件中
try:
    from fun_cal_sndr import cal_sndr
except ImportError:
    print("错误: 无法导入 fun_cal_sndr.py。请确保该文件存在且路径正确。")
    # 定义一个假的cal_sndr函数，以便在没有真实函数的情况下程序仍能运行
    def cal_sndr(data, fs, fb, window):
        print("警告: 正在使用假的 cal_sndr 函数!")
        fft_len = len(data)
        fft_freq = np.fft.rfftfreq(fft_len, 1/fs)
        fft_data = np.abs(np.fft.rfft(data))**2
        return 80.0, 13.0, 1e-5, 317.0, fft_data, fft_freq, -100.0, -90.0

##########################################  USER DEFINE  ###################################

# --- FFT 和 ADC 参数 ---
FS = 10000000 / 80 / 12*2  # 采样率 (~10.42 kHz)
FB = FS // 2             # 信号带宽
ADC_BITS = 12
FFT_POINTS = 65536       # FFT点数

# --- 通道和网络配置 ---
CHANNEL_TO_PLOT = 239    # 要实时监控的通道
HOST = '192.168.2.10'
PORT = 7
CHANNELS_TOTAL = 256
BYTES_PER_POINT = 4

# --- 线程通信 ---
RAW_DATA_QUEUE = queue.Queue(maxsize=100) 
SORTED_DATA_DEQUE = collections.deque()
SORTED_DATA_LOCK = threading.Lock()
STOP_EVENT = threading.Event()

###########################################  DEFINE END   ########################################

def receiver_thread(host, port, raw_queue, stop_event):
    """线程1: 接收者 - 从TCP socket接收数据"""
    print("接收线程已启动...")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((host, port))
        s.sendall("ctread".encode())
        print("接收线程：连接成功。")
        while not stop_event.is_set():
            data_chunk = s.recv(8192) # 增加单次接收字节数
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
    """线程2: 分拣者 - 拆分数据并放入共享deque"""
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

            if len(sorted_samples) > 0:
                with sorted_lock:
                    sorted_deque.extend(sorted_samples)

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

def fft_plotter_thread(sorted_deque, sorted_lock, fft_points, adc_bits, fs, fb, stop_event):
    """线程3: FFT绘图者 - [已修正shape mismatch问题]"""
    print("FFT绘图线程已启动...")
    
    try:
        plt.ion()
        fig, ax = plt.subplots(figsize=(12, 7))
        fig.canvas.mpl_connect('close_event', on_close)
        
        # --- 初始化绘图元素 ---
        # 先用空的占位符数据创建线条对象
        line, = ax.semilogx([], [])
        
        # 初始化文本框
        stats_text = 'Waiting for data...'
        text_box = AnchoredText(stats_text, loc='upper right', frameon=True)
        text_box.patch.set_boxstyle("round,pad=0.5,rounding_size=0.2")
        ax.add_artist(text_box)
        
        # 设置图表格式
        ax.set_title(f"Real-time FFT Spectrum (Channel {CHANNEL_TO_PLOT})")
        ax.set_xlabel('Frequency / Hz')
        ax.set_ylabel('Amplitude (dBFS)')
        ax.grid(True, which="both", ls="--")
        ax.set_ylim(-160, 10)
        # 初始xlim可以设置一个大概范围，后面会动态更新
        ax.set_xlim(1, fs/2)
        
        plot_initialized = False # 添加一个标志位，用于首次绘图时设置坐标轴范围

        while not stop_event.is_set():
            frame_data_int = None
            
            with sorted_lock:
                if len(sorted_deque) >= fft_points:
                    frame_data_int = np.array([sorted_deque.popleft() for _ in range(fft_points)])

            if frame_data_int is not None:
                frame_data_v = frame_data_int / (2**adc_bits) * 1.8
                
                print("数据帧已满，开始计算FFT...")
                # --- 【核心修改点 1】: 同时接收 fft_freq 和 fft_data ---
                sndr, enob, irn, fin, fft_data, fft_freq, irn_pow, thd = cal_sndr(frame_data_v, fs, fb, 'hann')
                print(f"计算完成: SNDR={sndr:.2f} dB, ENOB={enob:.2f} bits")

                y_data_db = 10 * np.log10(fft_data)
                
                # --- 【核心修改点 2】: 使用 set_data 同时更新X和Y轴 ---
                line.set_data(fft_freq, y_data_db)
                
                # 首次绘图后，根据实际频率范围调整X轴，避免范围不匹配
                if not plot_initialized and len(fft_freq) > 1:
                    ax.set_xlim(fft_freq[1], fs/2) # 从第二个频点开始，避免log(0)
                    plot_initialized = True

                new_text_content = (
                    f'Freq: {fin:.2f} Hz\n'
                    f'SNDR: {sndr:.2f} dB\n'
                    f'ENOB: {enob:.2f} bits\n'
                    f'THD: {thd:.2f} dB\n'
                    f'IRN: {irn/60*1e6:.2f} uVrms'
                )
                text_box.txt.set_text(new_text_content)
                
                fig.canvas.draw()
                fig.canvas.flush_events()
            else:
                time.sleep(0.1)
                fig.canvas.flush_events()

    except Exception as e:
        if "application has been destroyed" not in str(e):
             print(f"绘图线程错误: {e}")
    finally:
        print("绘图线程已关闭。")
        stop_event.set()

if __name__ == "__main__":
    receiver = threading.Thread(target=receiver_thread, args=(HOST, PORT, RAW_DATA_QUEUE, STOP_EVENT))
    sorter = threading.Thread(target=sorter_thread, args=(RAW_DATA_QUEUE, SORTED_DATA_DEQUE, SORTED_DATA_LOCK, CHANNEL_TO_PLOT, STOP_EVENT))
    plotter = threading.Thread(target=fft_plotter_thread, args=(SORTED_DATA_DEQUE, SORTED_DATA_LOCK, FFT_POINTS, ADC_BITS, FS, FB, STOP_EVENT))

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