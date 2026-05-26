import socket
import matplotlib.pyplot as plt
import os
import numpy as np
from datetime import datetime
import time
import multiprocessing
import math
##########################################  USER DEFINE  ###################################
SIZE_PLOT=1024*400 
save=0 # 0: no save, 1: save
sort=1 # 0: no sort, 1: sort list channels ,2: sort all data into channels channels
plot=1 # 0: no plot, 1: plot multiple channels in one figure 
#plotchannel_list=[160,161,162,163,192,193,194,195,223,224,225,226,227,228,229,230,231]
plotchannel_list=[195]
sortlist=plotchannel_list
dir = r"d:\ADC_data"
plot_dir='1030_2119'
HOST = '192.168.2.10'  
PORT = 7
channels=256
SIZE_TCPIP_SEND_BUF_TRUNK=4096
TCP_PACKET_CT=SIZE_TCPIP_SEND_BUF_TRUNK//4
TCP_TOTAL=1*1024*1024*100
Count_max=TCP_TOTAL//TCP_PACKET_CT
BYTES_DATA_POINTS=4 # 4 bytes per data point
fs=10000000/12/80
###########################################  DEFINE END   ########################################
time_sample=list([a/fs for a in range(SIZE_PLOT//4)])
# 获取当前时间
if save==0:
    plotdir = os.path.join(dir, plot_dir)
    savedir=plotdir
else:
    current_time = datetime.now()
    month = current_time.month
    day = current_time.day
    hour = current_time.hour
    minute = current_time.minute
    savedir = os.path.join(dir, f'{month:02d}{day:02d}_{hour:02d}{minute:02d}')
    plotdir=savedir
os.makedirs(savedir, exist_ok=True)
bty_file_write= plotdir+  "/"+ "ADC_DATA"+".bin"
print(f"开始接收数据\n")
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
        s.close()
    print("TCP传输完成，开始分拣为256通道")
if save==2:
    # wait 10s
    time.sleep(10) 
    print(f"Received finish\n")  

print(f"Received finish+++++++\n")  


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





