import socket
import matplotlib.pyplot as plt
import os
import numpy as np
from datetime import datetime
import time
import multiprocessing
import math
##########################################  USER DEFINE  ###################################

save=0 # 0: no save, 1: save
sort=0 # 0: no sort, 1: sort list channels ,2: sort all data into channels channels
plot=2 # 0: no plot, 1: plot rst 2:plot all
plotchannel_list=[160,161,162,163,192,193,194,195,223,224,226,227,228,229,230,231]
#plotchannel_list=[192,193,194,195]
#plotchannel_list=[227]
#plotchannel_list=np.linspace(0,255,256,dtype=int)
sortlist=plotchannel_list
dir = r"d:\ADC_data"
plot_dir='0530_2113'
HOST = '192.168.2.10'  
PORT = 7
channels=256
SIZE_TCPIP_SEND_BUF_TRUNK=4096
TCP_PACKET_CT=SIZE_TCPIP_SEND_BUF_TRUNK//4
TCP_TOTAL=1*1024*1024*80
SIZE_PLOT=TCP_TOTAL//256
Count_max=TCP_TOTAL//TCP_PACKET_CT
BYTES_DATA_POINTS=4 # 4 bytes per data point
fs=10000000/12/80
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
    with open(target_file_path, 'ab') as target_file:
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
#savedir=os.path.join(dir, plot_dir)    单独调试分拣时使用
sortch_folder =os.path.join(savedir, 'channel')
os.makedirs(sortch_folder, exist_ok=True)
if __name__ == "__main__":
    if sort==1:
        start_time = time.time()
        with multiprocessing.Pool() as pool:
            pool.map(sort_onechannel, range(len(sortlist)))
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"程序执行时间：{execution_time}秒")
        print("数据分拣完成") 

    if sort==2:
        bty_file_read=bty_file_write
        source_file_size = os.path.getsize(bty_file_read)
        savedir=os.path.join(dir, plot_dir)
        sortch_folder =os.path.join(savedir, 'channel')
        os.makedirs(sortch_folder, exist_ok=True)
        target_files = []
        for i in range(channels):
            target_file_path = os.path.join(sortch_folder, f'NL_channel_{i}.bin')
            target_files.append(open(target_file_path, 'ab'))
        bty_file_read=bty_file_write
        source_file_size = os.path.getsize(bty_file_read)
        # 初始化目标文件列表
        start_time = time.time()
        with open(bty_file_read, 'rb') as source_file:
            try:
                for index in range(channels):
                    file_channel=bytearray(source_file_size//channels)
                    cnt=0
                    while cnt<source_file_size//channels//BYTES_DATA_POINTS:
                        source_file.seek(cnt*channels*BYTES_DATA_POINTS+index*BYTES_DATA_POINTS)
                        file_channel[cnt*BYTES_DATA_POINTS:(cnt+1)*BYTES_DATA_POINTS]=source_file.read(BYTES_DATA_POINTS)
                        cnt=cnt+1
                    target_files[index].write(file_channel)
                    target_files[index].close()
            finally:
                source_file.close()
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
        for channel_index in plotchannel_list:
            file_path = os.path.join(plot_folder, f'NL_channel_{channel_index}.bin')
            with open(file_path, 'rb') as h_file_results:
                h_file_results.seek(BYTES_DATA_POINTS*2)
                data = h_file_results.read(SIZE_PLOT)
                data = process_data(data)
                data2=np.array(data)/4096*1.8
                if 0.1 < np.mean(data2) < 1.6 and np.std(data2) < 0.05:
                    cnt_right += 1
                    print(channel_index)
                    all_data.append(data)
                    channel_labels.append(f'Channel {channel_index}')

        all_data = np.array(all_data)/4096*1.8
        plt.figure(figsize=(10, 6))
        for data, label in zip(all_data, channel_labels):
            plt.plot(time_sample, data, label=label)
        plt.title("ADC Data")
        plt.xlabel("Time/s")
        plt.ylabel("ADC Value")
        plt.legend()
        plt.show()
        print(f"Right channels: {cnt_right}")
    if plot==2:
        all_data = []
        channel_labels = []
        for channel_index in plotchannel_list:
            file_path = os.path.join(plot_folder, f'NL_channel_{channel_index}.bin')
            with open(file_path, 'rb') as h_file_results:
                h_file_results.seek(BYTES_DATA_POINTS*2)
                data = h_file_results.read(SIZE_PLOT)
                data = process_data(data)
                all_data.append(data)
                channel_labels.append(f'Channel {channel_index}')
        all_data = np.array(all_data)/4096*1.8
        plt.figure(figsize=(10, 6))
        for data, label in zip(all_data, channel_labels):
            plt.plot(data, label=label)
        plt.title("ADC Data")
        plt.xlabel("Sample")
        plt.ylabel("ADC Value")
        plt.legend()
        plt.show()
    if plot == 3:
        all_data = []
        channel_labels = []
        colors = ['b', 'g', 'r', 'c', 'm', 'y', 'k']
        # Check the length of the channel list
        num_channels = len(plotchannel_list)
        rows = int(math.sqrt(num_channels))
        cols = int(math.ceil(num_channels / rows))
        fig, axes = plt.subplots(rows, cols, figsize=(12, 8))
        for i, channel_index in enumerate(plotchannel_list):
            file_path = os.path.join(plot_folder, f'NL_channel_{channel_index}.bin')
            with open(file_path, 'rb') as h_file_results:
                h_file_results.seek(BYTES_DATA_POINTS * 2)
                data = h_file_results.read(SIZE_PLOT)
                data = process_data(data)
                all_data.append(data)
                channel_labels.append(f'Channel {channel_index}')
            row, col = divmod(i, cols)
            ax = axes[row, col] if num_channels > 1 else axes  # Handle single subplot case
            data = np.array(data) 
            color = colors[i % len(colors)]
            ax.plot(time_sample,data, color=color)
            ax.set_title(f'Channel {channel_index}')
            ax.set_xlabel("Time/s")
            ax.set_ylabel("Voltage/V")
            ax.legend()

        # Remove empty subplots (if any)
        if num_channels < (rows * cols):
            for i in range(num_channels, rows * cols):
                fig.delaxes(axes[divmod(i, cols)])
        #fig.suptitle("Nueral-link 256 channels ADC data", fontsize=16)  # Add a big title
        plt.tight_layout()  # Adjust layout to make room for the big title
        plt.show()