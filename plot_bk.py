import socket
import matplotlib.pyplot as plt
import os
import numpy as np
from datetime import datetime
import time
import multiprocessing
import math
from fun_cal_sndr import cal_sndr
from matplotlib.offsetbox import AnchoredText

##########################################  USER DEFINE  ###################################

save=1 # 0: no save, 1: save
sort=1 # 0: no sort, 1: sort list channels ,2: sort all data into channels channels
plot=1 # 0: no plot, 1: plot rst 2:plot all

# --- 新增的绘图开关 (1: 绘制, 0: 不绘制) ---
plot_reconstruction = 0  # 时间域 "ADC Data Reconstruction" 图
plot_reconstruction_points = 1  # 时间域 "ADC Data Reconstruction" 图，X轴为点数
plot_fft = 1             # 频谱 "FFT Spectrum" 图
plot_adc_bits = 0       # "ADC 数字码流分布" 直方图
# -----------------------------------------

plotchannel_list=[239]
sortlist=plotchannel_list
dir = r"d:\ADC_data"
plot_dir='0617_1529'
HOST = '192.168.2.10'  
PORT = 7
channels=256
SIZE_TCPIP_SEND_BUF_TRUNK=4096
SIZE_1=4096*10000000/12/80//4
offset_time=10
SIZE_OFF=offset_time*SIZE_1
TCP_PACKET_CT=SIZE_TCPIP_SEND_BUF_TRUNK//4
TCP_TOTAL=1*1024*1024*48
SIZE_PLOT=TCP_TOTAL//256
Count_max=TCP_TOTAL//TCP_PACKET_CT
BYTES_DATA_POINTS=4 # 4 bytes per data point
fs=10000000/12/80*2
fb=fs//2
dummy=1
fft_points = 16384

###########################################  DEFINE END   ########################################
time_sample=list([a/fs for a in range(SIZE_PLOT//4)])
# 获取当前时间
current_time = datetime.now()
month = current_time.month
day = current_time.day
hour = current_time.hour
minute = current_time.minute
savedir = os.path.join(dir, f'{month:02d}{day:02d}_{hour:02d}{minute:02d}')
if save==0:
    plotdir = os.path.join(dir, plot_dir)
else:
    plotdir=savedir
os.makedirs(savedir, exist_ok=True)
bty_file_write= plotdir+  "/"+ "ADC_DATA"+".bin"



def getADC_bits(data_recv, resolution_bits):
    """

    """
    # --- 字体与样式配置 (更稳健的设置) ---
    plt.rcParams['font.sans-serif'] = ['SimHei']  # 指定使用中文字体
    plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
    
    # --- 数据处理 ---
    resolution = 2 ** resolution_bits
    data = data_recv % resolution
    data_min = np.min(data)
    data_max = np.max(data)
    x = np.arange(data_min, data_max + 1)
    y = np.zeros(len(x), dtype=int)
    for z_idx, code in enumerate(x):
        y[z_idx] = np.sum(data == code)
    
    # --- 绘图 (优化布局) ---
    # 使用更适合论文的尺寸(8x5英寸)，并设置高分辨率DPI
    fig, ax = plt.subplots(figsize=(8, 5), dpi=300)

    # 绘制条形图
    ax.bar(x, y, color='#4285F4', edgecolor='black', linewidth=0.5)
    
    # 设置标题和标签
    ax.set_title("12-bit SAR ADC Code Distribution", fontsize=16, fontweight='bold', pad=15)
    ax.set_xlabel("12-bit ADC 数字码流 (ADC Code)", fontsize=14)
    ax.set_ylabel("频数 (Counts)", fontsize=14)
    
    # 设置刻度
    ax.tick_params(axis='both', which='major', labelsize=12, direction='in')
    
    # 设置网格线
    ax.grid(axis='y', linestyle='--', alpha=0.6)
    
    # 移除顶部和右侧的边框
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    # --- 动态计算标注文本的位置 ---
    nonzero_counts = np.count_nonzero(y)
    # X位置: 位于图表X轴范围的98%处
    # Y位置: 位于图表Y轴范围的95%处
    x_pos = ax.get_xlim()[0] + 0.98 * (ax.get_xlim()[1] - ax.get_xlim()[0])
    y_pos = ax.get_ylim()[0] + 0.95 * (ax.get_ylim()[1] - ax.get_ylim()[0])

    ax.text(x_pos, y_pos, f'Non-zero Steps: {nonzero_counts}', 
            ha='right', va='top', fontsize=12,
            bbox=dict(boxstyle="round,pad=0.3", fc='white', ec='black', lw=0.5, alpha=0.8))

    # 调整子图布局，为标签留出更多空间
    fig.subplots_adjust(left=0.12, bottom=0.15)
    
    return fig, ax




def recieve_tcpip (conn,num_to_recieve,max_attemp=-1):
    cnt_attemp=0
    data=bytearray()
    while ((num_to_recieve >0) and (cnt_attemp<=max_attemp or max_attemp==-1)):
        rx_data = []
        cnt_attemp = cnt_attemp + 1
        rx_data = conn.recv(min(num_to_recieve,SIZE_TCPIP_SEND_BUF_TRUNK))
        data.extend(rx_data)  
        len_recv_data=len(rx_data)   
        num_to_recieve=num_to_recieve-len_recv_data
    return data

def process_data(data):
    values = np.zeros(len(data)//BYTES_DATA_POINTS)
    for i in range(0, len(data), BYTES_DATA_POINTS):
        values[i//BYTES_DATA_POINTS] = int.from_bytes(data[i:i+BYTES_DATA_POINTS], byteorder='little')
    return values

def sort_onechannel(index):
    target_file_path = os.path.join(sortch_folder, f'NL_channel_{sortlist[index]}.bin')
    file_channel=bytearray(source_file_size//channels)
    with open(target_file_path, 'wb') as target_file:
        with open(bty_file_read, 'rb') as source_file:
            try:
                cnt = 0
                while cnt < source_file_size // channels // BYTES_DATA_POINTS:
                    source_file.seek(cnt * channels * BYTES_DATA_POINTS + sortlist[index] * BYTES_DATA_POINTS)
                    file_channel[cnt * BYTES_DATA_POINTS:(cnt + 1) * BYTES_DATA_POINTS] = source_file.read(BYTES_DATA_POINTS)
                    cnt += 1
                target_file.write(file_channel)
            finally:
                source_file.close()
                target_file.close()

if save==1:
    # 定义目标文件夹路径
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((HOST, PORT))
        message = "ctread"
        s.sendall(message.encode())
        cnt_ctread=0
        with open(bty_file_write,"ab+") as h_file_results:
            h_file_results.seek(0)
            h_file_results.truncate()
            while cnt_ctread<Count_max:
                recv_data =recieve_tcpip(s,TCP_PACKET_CT)
                h_file_results.write(recv_data)
                cnt_ctread += 1
        print(f"Received finish\n")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # 关闭连接
        s.close()
    print("TCP传输完成，开始分拣为256通道")
    

bty_file_read=bty_file_write
source_file_size = os.path.getsize(bty_file_read)

sortch_folder =os.path.join(savedir, 'channel')
os.makedirs(sortch_folder, exist_ok=True)

if sort==1:
    start_time = time.time()
    for i in range(len(sortlist)):
        sort_onechannel(i)
    end_time = time.time()
    execution_time = end_time - start_time
    print(f"程序执行时间：{execution_time}秒")
    print("数据分拣完成") 
    
plot_folder = os.path.join(plotdir, 'channel')
os.makedirs(plot_folder, exist_ok=True)

if plot==1:
    cnt_right=0
    all_data = []
    channel_labels = []
    excluded_channels = []
    for channel_index in plotchannel_list:
        file_path = os.path.join(plot_folder, f'NL_channel_{channel_index}.bin')
        with open(file_path, 'rb') as h_file_results:
            h_file_results.seek(BYTES_DATA_POINTS*0)
            data = h_file_results.read(SIZE_PLOT)
            # 保存原始整数数据
            data_raw = process_data(data)
            all_data.append(data_raw)
            channel_labels.append(f'Channel {channel_index}')

    # 将数据统一转换为电压值，用于绘图
    all_data_scaled = np.array(all_data)/4096*1.8

    # --- 图 1: ADC Data Reconstruction (时间域) ---
    if plot_reconstruction == 1:
        plt.figure(figsize=(10, 6))
        for data, label in zip(all_data_scaled, channel_labels):
            plt.plot(time_sample, data, label=label)
        plt.title("ADC Data Reconstruction")
        plt.xlabel("Time/s")
        plt.ylabel("Amplitude/V")
        plt.legend()
        plt.show()
    # --- 图 1: ADC Data Reconstruction (时间域) ---
    if plot_reconstruction_points == 1:
        num_points = len(all_data_scaled[0])
        
        # 2. 生成新的X轴，值为 [0, 4, 8, 12, ...]
        x_axis_new = [i * 3 for i in range(num_points)]
        plt.figure(figsize=(10, 6))
        for data, label in zip(all_data_scaled, channel_labels):
            plt.plot(x_axis_new, data, label=label)
        plt.title("ADC Data Reconstruction")
        plt.xlabel("Points")
        plt.ylabel("Amplitude/V")
        plt.legend()
        plt.show()
    # --- 图 2: FFT Spectrum ---
    if plot_fft == 1:
        plt.figure(figsize=(10, 6))
        all_irn = []
        valid_irn_channels = []

        for channel_index, data in zip(plotchannel_list, all_data_scaled):
            # 注意: 确保data长度足够
            if len(data) >= fft_points * 2:
                data_segment = data[fft_points:fft_points+fft_points]
            else:
                data_segment = data # 如果数据不够，使用全部数据
            
            sndr, enob, irn, fin, fft_data, fft_freq, irn_pow, thd = cal_sndr(data_segment, fs, fb, 'hann')
            
            all_irn.append(irn * 1e6)  # μV_rms
            valid_irn_channels.append(channel_index)

            plt.semilogx(fft_freq, 10 * np.log10(np.abs(fft_data)), label=f'Ch{channel_index}')

        if len(all_irn) > 0:
            irn_array = np.array(all_irn) / 60  # 等效到输入
            mean_val = np.mean(irn_array)
            std_val = np.std(irn_array)
            min_val = np.min(irn_array)
            max_val = np.max(irn_array)

            stats_text = (
                f"IRN Mean: {mean_val:.2f} μV_rms\n"
                f"IRN Std: {std_val:.2f} μV_rms\n"
                f"Min: {min_val:.2f} μV_rms\n"
                f"Max: {max_val:.2f} μV_rms"
            )

            ax = plt.gca()  # 获取当前子图
            text_box = AnchoredText(stats_text, loc='upper right', prop=dict(size=10))
            text_box.patch.set_boxstyle("round,pad=0.3,rounding_size=0.2")
            text_box.patch.set_alpha(0.8)
            text_box.patch.set_facecolor('white')
            ax.add_artist(text_box)

        ax = plt.gca()
        ax.set_xlabel("Frequency (Hz)")
        ax.set_ylabel("Amplitude (dB)")
        plt.title("FFT Spectrum of Selected Channels")
        plt.grid(True, which="both", ls="--")
        plt.tight_layout()
        plt.show()

    # --- 图 3: ADC 数字码流分布 ---
    if plot_adc_bits == 1:
        # 使用第一个通道的原始整数数据来绘制分辨率图
        if len(all_data) > 0:
            getADC_bits(all_data[0], 12)
            plt.show()
        else:
            print("No data available to plot ADC bits distribution.")

