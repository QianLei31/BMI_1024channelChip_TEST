import socket
import binascii
from matplotlib.offsetbox import AnchoredText
import matplotlib.pyplot as plt
import ttkbootstrap as tk
from ttkbootstrap.constants import *
import os
import numpy as np
from numpy import sin, pi
from scipy import signal
import spi_mode
from spi_mode import *
from fun_cal_sndr import cal_sndr
import subprocess
from datetime import datetime


HOST = '192.168.2.10'  
PORT = 7 
SIZE_TCPIP_SEND_BUF_TRUNK=4096
TCP_PACKET_CT=SIZE_TCPIP_SEND_BUF_TRUNK
TCP_TOTAL=1*1024*1024*2048
Count_max=TCP_TOTAL//TCP_PACKET_CT
BYTES_DATA_POINTS=4
ADC_bits=12
fs=10000000/12/80*2
fb=fs//2
dt_read_cnt=15
NUM_DATA_POINTS_READ=dt_read_cnt*SIZE_TCPIP_SEND_BUF_TRUNK//4
global data_recv_init
global data_rec
data_recv_init=bytearray()
data_rec=np.zeros(NUM_DATA_POINTS_READ)


def save_data():
    global data_recv_init
    desdir = r"d:\testchip_results"
    strPathSave = desdir +"/" +"NL"
    os.makedirs(strPathSave, exist_ok=True)
    str_file_write= strPathSave+  "/"+ "ADC_DATA"+".bin"


    current_time = datetime.now() 
    month = current_time.month
    day = current_time.day
    hour = current_time.hour
    minute = current_time.minute
    second = current_time.second
    savedir = os.path.join(strPathSave, f'{month:02d}{day:02d}_{hour:02d}{minute:02d}_{second}')
    os.makedirs(savedir, exist_ok=True)
    str_file_write= savedir+  "/"+ "ADC_DATA"+".bin"
    if len(data_recv_init)==0:
        console_output.insert(tk.END, f"No data to save\n")
        console_output.insert(tk.END, f": {(data_recv_init[1:])}\n")
        return
    else:
        with open(str_file_write,"ab+") as h_file_results:
            h_file_results.write(data_recv_init)
            h_file_results.close()
        console_output.insert(tk.END, f"Save data to {str_file_write}\n")              
def process_data(data):
    values = np.zeros(len(data)//4)
    for i in range(0, len(data), 4):
        values[i//4] = int.from_bytes(data[i:i+4], byteorder='little')
    return values
def set_mode():
    #配置读取的通道
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # 连接服务
        s.connect((HOST, PORT))
        block_data=entry_block.get()
        binary_data = bytearray(int(block_data[i:i+8], 2) for i in range(0, len(block_data), 8))
        hex_data = binascii.hexlify(binary_data).decode()
        message = "set"+ hex_data
        console_output.insert(tk.END, f"{message}\n")
        s.sendall(message.encode())            
    except Exception as e:
        console_output.insert(tk.END, f"Connect Error: {e}\n")
    finally:
        # 关闭连接
        s.close()
    
def dt_read_mode():
    global data_recv_init
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((HOST, PORT))
        message = "read"
        cnt=0
        s.sendall(message.encode())
        data_rec=np.zeros(NUM_DATA_POINTS_READ)
        # 接收服务器返回的数据
        cnt_read_mem = 0
        while cnt_read_mem < dt_read_cnt:
            recv_data = recieve_tcpip(s,SIZE_TCPIP_SEND_BUF_TRUNK)
            data_recv_init.extend(recv_data)
            console_output.insert(tk.END, f"Received amount: {len(recv_data)}\n")
            # 将数据解析为整数列表
            data_list = np.array(process_data(recv_data))/4096*1.8
            data_rec[cnt_read_mem*SIZE_TCPIP_SEND_BUF_TRUNK//4:(cnt_read_mem+1)*SIZE_TCPIP_SEND_BUF_TRUNK//4]=data_list
            cnt_read_mem = cnt_read_mem + 1
            # 绘制图形
        
        cnt=cnt+1
        time_sample=list([a/fs for a in range(NUM_DATA_POINTS_READ)])
        plt.ion()
        console_output.insert(tk.END, f"Max: {max(data_rec[1:])}\n")
        console_output.insert(tk.END, f"Min: {min(data_rec[1:])}\n")
        fig, ax = plt.subplots()  # 创建图形对象和轴对象
        len1=len(data_rec[1:])
        '''time_sample[0:len1],'''
        ax.plot(time_sample[1:],data_rec[1:],c='r')
        max_value = max(data_rec[1:])
        min_value = min(data_rec[1:])
        AMP=max_value-min_value
        sndr,enob,irn,fin,fft_data,fft_freq,irn,thd= cal_sndr(data_rec[1:8193],fs,fb,'hann')
        #cal_snr(data_rec[1:],fs/2,fs)
        text_content = f'Max:{max_value:.4f} V \nMin:{min_value:.4f} V \nAMP:{AMP:.4f} V \nFin: {fin:.2f} Hz'
        text_box = AnchoredText(text_content, loc='upper right')
        text_box.patch.set_boxstyle("round,pad=0.,rounding_size=0.2")
        ax.add_artist(text_box)
        ax.set_xlabel('TIME (s)')
        ax.set_ylabel('ADC VALUE (V)')
        plt.title("ADC Data Reconfiguration")
        plt.pause(0.001)
        #plt.figure(figsize=(8, 6))
        #getADC_bits(data_rec[1:]/1.8*4096,ADC_bits)
        #plt.show()
                               
    except Exception as e:
        console_output.insert(tk.END, f"Connect Error: {e}\n")
    finally:
        # 关闭连接
        s.close()
def dt_getdata():
    #为CT模式准备数据
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((HOST, PORT))
        message = "read"
        cnt=0
        s.sendall(message.encode())
        data_rec=np.zeros(NUM_DATA_POINTS_READ)
        # 接收服务器返回的数据
        cnt_read_mem = 0
        while cnt_read_mem < dt_read_cnt:
            recv_data = recieve_tcpip(s,SIZE_TCPIP_SEND_BUF_TRUNK)
            data_recv_init.extend(recv_data)
            console_output.insert(tk.END, f"Received amount: {len(recv_data)}\n")
            # 将数据解析为整数列表
            data_list = np.array(process_data(recv_data))/4096*1.8
            data_rec[cnt_read_mem*SIZE_TCPIP_SEND_BUF_TRUNK//4:(cnt_read_mem+1)*SIZE_TCPIP_SEND_BUF_TRUNK//4]=data_list
            cnt_read_mem = cnt_read_mem + 1
    # 绘制图形
    except Exception as e:
        console_output.insert(tk.END, f"Connect Error: {e}\n")
    finally:
        # 关闭连接

        s.close()
        
    return data_rec    
def ct_read_mode_new():
    def on_close(event):
        nonlocal window_closed
        window_closed = True

    window_closed = False
    ct_cnt = 0
    fig, ax = plt.subplots()
    fig.canvas.mpl_connect('close_event', on_close)

    data_plot = dt_getdata()
    time_sample = list([a/fs for a in range(NUM_DATA_POINTS_READ)])
    xdata = time_sample[1:]
    ydata = data_plot[1:]
    line, = plt.plot(xdata, ydata)
    plt.ylim(0, 1.8)  # 设置 y 轴范围

    while ct_cnt < 100:
        if window_closed:
            break
        data_plot = dt_getdata()
        xdata = time_sample[1:]
        ydata = data_plot[1:]
        max_value = max(ydata[1:])
        min_value = min(ydata[1:])
        AMP = max_value - min_value
        sndr, enob, irn, fin, fft_data, fft_freq, irn, thd = cal_sndr(ydata[1:8193], fs, fb, 'hann')

        text_content = f'Max:{max_value:.4f} V \nMin:{min_value:.4f} V \nAMP:{AMP:.4f} V \nFin: {fin:.2f} Hz'
        text_box = AnchoredText(text_content, loc='upper right')
        text_box.patch.set_boxstyle("round,pad=0.,rounding_size=0.2")
        ax.add_artist(text_box)
        ax.set_xlabel('TIME (s)')
        ax.set_ylabel('ADC VALUE (V)')
        plt.title("ADC Data Reconfiguration")
        line.set_data(xdata, ydata)
        plt.pause(1.5)

        ct_cnt += 1
        
def plot_ADC_bits():
    # This list will hold the NumPy arrays from each call
    all_data_arrays = []
    i=0
    while i < 20:
        # FIX #3: Get the data array returned by the function
        single_run_data = dt_getdata()
        # Optional: Check if the function returned valid data before appending
        if single_run_data.size > 0:
            all_data_arrays.append(single_run_data)
        i=i+1
        print(f"Run {i} data collected, length: {len(single_run_data)}")


   # FIX #4: Combine all the arrays into one large array
    if all_data_arrays:
        final_data_array = np.concatenate(all_data_arrays)
        #get ADC bits
        getADC_bits(final_data_array*4096/1.8, ADC_bits)
        plt.show()
    else:
        print("No data was collected.")





def spi_mode():
    try:
        # 创建 TCP/IP socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # 连接服务
        s.connect((HOST, PORT))
        spi_cmd = entry_spi_cmd.get()  # 获取文本框中的SPI 命令
        spi_cmd=spi_cmd.replace("_","")
        spi_cmd = spi_cmd.zfill(64)
        binary_data = bytearray(int(spi_cmd[i:i+8], 2) for i in range(0, len(spi_cmd), 8))
        hex_data = binascii.hexlify(binary_data).decode()
        message = "spi" + hex_data
        console_output.insert(tk.END, f"{message}\n")
        console_output.insert(tk.END, f"Code: {spi_cmd[0:6]},Adder: {spi_cmd[6:16]},Data: {spi_cmd[16:32]}\n")
        s.sendall(message.encode())
        # 接收服务器返回的数据
        s.settimeout(10)
        data = s.recv(4100)
        
        console_output.insert(tk.END, f"Received amount: {len(data)}\n")
        for i in range(4, 12, 4):
            show_data=data[i:i+4]
            bina_data = []
            hex_data = binascii.hexlify(show_data).decode()
            hex_data="".join(reversed([hex_data[i:i+2] for i in range(0, len(hex_data), 2)]))
            hex_data_pr=bin(int(hex_data, 16))[2:].zfill(32)
            #console_output.insert(tk.END, f"{hex_data}\n")
            #console_output.insert(tk.END, f"{hex_data_pr}\n")
            ADC_data=hex_data_pr[20:32]
            if hex_data_pr[0:6]=='010011':
                console_output.insert(tk.END, f"Received:  Code: {hex_data_pr[0:6]} , Adder: {hex_data_pr[6:16]} , Data: {hex_data_pr[16:32]} , Value: {int(ADC_data,2)/4095*1.8} hex: {hex_data} , idx: {i}\n")
            else:
                console_output.insert(tk.END, f"Received:  Code: {hex_data_pr[0:6]} , Adder: {hex_data_pr[6:16]} , Data: {hex_data_pr[16:32]} , hex: {hex_data} , idx: {i}\n")
    except Exception as e:
        console_output.insert(tk.END, f"Connect Error: {e}\n")

    finally:
        # 关闭连接
        s.close()
def clear_console_output():
    console_output.delete(1.0, tk.END)
def REC_MUTI():
    script_directory=os.path.dirname(os.path.realpath(__file__))
    script_path1 = os.path.join(script_directory, "plot_multichannel.py")
    subprocess.run(["python", script_path1])
def STIM_REC(console_output):
     Stim_ELE16(console_output)
     dt_read_mode()
def REC_Single():
    script_directory=os.path.dirname(os.path.realpath(__file__))
    script_path1 = os.path.join(script_directory, "plot_singlechannel_fft.py")
    subprocess.run(["python", script_path1])   
    
window = tk.Tk()
window.title("TEST_CHIP")
window.geometry("1200x800")
# Console Output
console_output = tk.Text(window, height=10)
console_output.place(relx=0, rely=0, anchor=tk.NW, relwidth=0.5, relheight=0.8)
scrollbar = tk.Scrollbar(console_output)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
console_output.config(yscrollcommand=scrollbar.set)
scrollbar.config(command=console_output.yview)
# SPI Command Entry
label_spi_cmd = tk.Label(window, text="SPI 命令：")
label_spi_cmd.place(relx=0, rely=0.86, anchor=tk.NW)
entry_spi_cmd = tk.Entry(window, width=65)
entry_spi_cmd.place(relx=0.05, rely=0.86, anchor=tk.NW)
button_spi = tk.Button(window, text="Send SPI", command=spi_mode)
button_spi.place(relx=0.445, rely=0.855, anchor=tk.NW)
# Clear Console Button
button_clear_output = tk.Button(window, text="Clear Console", command=clear_console_output)
button_clear_output.place(relx=0.25, rely=0.81, anchor=tk.N)
# SET Mode Button
lable_entry_block = tk.Label(window, text="Read Block:")
lable_entry_block.place(relx=0, rely=0.93, anchor=tk.NW)
entry_block = tk.Entry(window, width=15)
entry_block.place(relx=0.16, rely=0.935, anchor=tk.NE)
button_set = tk.Button(window, text="Set Channel", command=set_mode)
button_set.place(relx=0.23, rely=0.93, anchor=tk.N)
# Read Mode Buttons
button_read_dt = tk.Button(window, text="DT_Read", command=dt_read_mode)
button_read_dt.place(relx=0.31, rely=0.93, anchor=tk.N)
button_read_ct = tk.Button(window, text="CT_Read", command=ct_read_mode_new)
button_read_ct.place(relx=0.39, rely=0.93, anchor=tk.N)
# Save Data Button
button_save = tk.Button(window, text="Plot ADC Bits", command=plot_ADC_bits)
button_save.place(relx=0.47, rely=0.93, anchor=tk.N)
# Buttons for Functions
functions_frame = tk.Frame(window)
functions_frame.place(relx=0.5, rely=0, anchor=tk.NW, relwidth=0.5, relheight=0.8)
# Adder Entry
adder_label = tk.Label(window, text="adder:")
adder_label.place(relx=0.65, rely=0.8, anchor=tk.E)
adder_entry = tk.Entry(window)
adder_entry.place(relx=0.75, rely=0.8, anchor=tk.CENTER)
# Data Entry
data_label = tk.Label(window, text="data:")
data_label.place(relx=0.65, rely=0.85, anchor=tk.E)
data_entry = tk.Entry(window)
data_entry.place(relx=0.75, rely=0.85, anchor=tk.CENTER)
# Stim ELECTRODE
Stim_ELE_lable = tk.Label(window, text="Stim_ele(/channel):")
Stim_ELE_lable.place(relx=0.65, rely=0.90, anchor=tk.E)
Stim_ELE_entry = tk.Entry(window)
Stim_ELE_entry.place(relx=0.75, rely=0.90, anchor=tk.CENTER)
#Stim AMP
Stim_AMP_lable = tk.Label(window, text="Stim_amp(9bit):")
Stim_AMP_lable.place(relx=0.65, rely=0.95, anchor=tk.E)
Stim_AMP_entry = tk.Entry(window)
Stim_AMP_entry.place(relx=0.75, rely=0.95, anchor=tk.CENTER)
# Calculate vertical spacing between buttons
vertical_spacing = 0.08
button_top = 0.02
button_height = 2
button_width = 20
# Create buttons and adjust position using vertical_spacing
function_buttons = [
    ("Analog Reset", lambda: Analog_Reset(console_output)),
    ("Analog Remove Reset", lambda: Analog_RemoveReset(console_output)),
    ("Global DAC On", lambda: Global_DAC_On(console_output)),
    ("Global DAC Off", lambda: Global_DAC_Off(console_output)),
    ("SET CBOK LOW", lambda: SET_CBOK_LOW(console_output)),
    ("REC_single", lambda: REC_Single()),
    ("Read STIM", lambda: Read_STIM(console_output, adder_entry.get(), data_entry.get())),
    ("Write REC", lambda: Write_REC(console_output, adder_entry.get(), data_entry.get())),
    ("Read REC", lambda: Read_REC(console_output, adder_entry.get(), data_entry.get())),
    ("Dummy", lambda: Dummy(console_output)),
    #("Write ELECTRODE", lambda: Write_ELECTRODE(console_output, adder_entry.get(), data_entry.get())),
    #("Read ELECTRODE", lambda: Read_ELECTRODE(console_output, adder_entry.get(), data_entry.get())),
    ("Set Gain High", lambda: Set_global_gain_high(console_output)),
    ("Set Gain Low", lambda: Set_global_gain_low(console_output))
]
for text, command in function_buttons:
    button = tk.Button(functions_frame, text=text, command=command, width=button_width, height=button_height)
    button.place(relx=0.15, rely=button_top, anchor=tk.NW)
    button_top += vertical_spacing

button_top = 0.02
function_buttons1 = [
    ("STIM_ELE1", lambda: Stim_ELE1(console_output)),
    ("STIM_ELE2", lambda: Stim_ELE2(console_output)),
    ("STIM_ELE5", lambda: Stim_ELE5(console_output)),
    ("STIM_ELE6", lambda: Stim_ELE6(console_output)),
    ("STIM_ELE11", lambda: Stim_ELE11(console_output)),
    ("STIM_ELE12", lambda: Stim_ELE12(console_output)),
    ("STIM_ELE13", lambda: Stim_ELE13(console_output)),
    ("STIM_ELE14", lambda: Stim_ELE14(console_output)),
    ("STIM_ELE16", lambda: Stim_ELE16(console_output)),
    ("STIM+REC", lambda: STIM_REC(console_output)),

    ("REC_ELE16", lambda: REC_ELE16(console_output)),
    ("REC_MUti", lambda: REC_MUTI())
]
for text, command in function_buttons1:
    button = tk.Button(functions_frame, text=text, command=command, width=button_width, height=button_height)
    button.place(relx=0.45, rely=button_top, anchor=tk.NW)
    button_top += vertical_spacing


window.mainloop()