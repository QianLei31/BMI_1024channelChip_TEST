import socket
import binascii
import tkinter as tk
import time
HOST = '192.168.2.10'  
PORT = 7 
SIZE_TCPIP_SEND_BUF_TRUNK=4096
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
def single_TCP(spi_cmd,console_output):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # 连接服务
        s.connect((HOST, PORT))
        spi_cmd=spi_cmd.replace("_","")
        binary_data = bytearray(int(spi_cmd[i:i+8], 2) for i in range(0, len(spi_cmd), 8))
        hex_data = binascii.hexlify(binary_data).decode()
        message = "spi" + hex_data
        console_output.insert(tk.END, f"{message}\n")
        console_output.insert(tk.END, f"Code: {spi_cmd[0:6]}, Adder: {spi_cmd[6:16]}, Data: {spi_cmd[16:32]}\n")
        s.sendall(message.encode())
        # 接收服务器返回的数据
        s.settimeout(5)
        data = s.recv(12)
        #console_output.insert(tk.END, f"Received amount: {len(data)}\n")
        console_output.tag_config('red_font', font=('Arial', 10), foreground='red')
        for i in range(8, len(data), 4):
            show_data = data[i:i+4]
            bina_data = []
            hex_data = binascii.hexlify(show_data).decode()
            hex_data = "".join(reversed([hex_data[i:i+2] for i in range(0, len(hex_data), 2)]))
            hex_data_pr = bin(int(hex_data, 16))[2:].zfill(32)
            ADC_data = hex_data_pr[20:32]
            if hex_data_pr[0:6] == '010011':
                console_output.insert(tk.END, f"Received:  Code: {hex_data_pr[0:6]}, Adder: {hex_data_pr[6:16]}, Data: {hex_data_pr[16:32]}, Value: {int(ADC_data, 2)/4095*1.8} hex: {hex_data}\n",'red_font')
            else:
                console_output.insert(tk.END, f"Received:  Code: {hex_data_pr[0:6]}, Adder: {hex_data_pr[6:16]}, Data: {hex_data_pr[16:32]}, hex: {hex_data}\n",'red_font')
    except Exception as e:
        console_output.insert(tk.END, f"Connect Error: {e}\n")
    finally:
        # 关闭连接
        s.close()
def Analog_Reset(console_output):
    spi_cmd = "00011100000000000000000000000000"  
    single_TCP(spi_cmd,console_output)
    console_output.tag_config('custom_font', font=('Arial', 12), foreground='blue')
    console_output.insert(tk.END, f"Analog_Reset!!\n",'custom_font')
def Analog_RemoveReset(console_output):
    spi_cmd = "00100000000000000000000000000000"  
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"Analog_RemoveReset!!\n")
def Global_DAC_On(console_output):
    spi_cmd = "00100100000000000000000000000000"  
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"Global_DAC_On!!\n")
def Global_DAC_Off(console_output):
    spi_cmd = "00110100000000000000000000000000"  
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"Global_DAC_Off!!\n")
def SET_CBOK_LOW(console_output):
    spi_cmd = "01001000000000000000000000000000"  
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"SET_CBOK_LOW!!\n")
def Write_STIM(console_output,adder,data):
    code = "000110"  
    spi_cmd ="".join([code,adder,data])
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"Write_STIM!!\n")
def Read_STIM(console_output,adder,data):
    code = "000011"  
    spi_cmd = "".join([code,adder,data])
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"Read_STIM!!\n")
def Write_REC(console_output,adder,data):
    code = "000100"  
    spi_cmd = "".join([code,adder,data])
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"Write_REC!!\n")
def Read_REC(console_output,adder,data):
    code = "000001"  
    spi_cmd = "".join([code,adder,data])
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"Read_REC!!\n")
def Read_ADC(console_output,adder,data):
    code = "010011"  
    spi_cmd = "".join([code,adder,data])
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"Read_ADC!!\n")
def Write_ELECTRODE(console_output,adder,data):
    code = "010000"  
    spi_cmd = "".join([code,adder,data])
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"Write_ELCTRODE!!\n")
def Read_ELECTRODE(console_output,adder,data):
    code = "010001"  
    spi_cmd = "".join([code,adder,data])
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"Read_ELCTRODE!!\n")
def Dummy(console_output):
    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
def REC_ELE16(console_output):
    #ELE16 实测无问题
    console_output.tag_config('custom_font', font=('Arial', 12), foreground='blue')
    
    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)
    
    #spi_cmd = "010000_0011000000_1111011001010000"
    spi_cmd = "010000_0011000000_1110100000000001"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************配置block48电极************\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

    spi_cmd = "01000100110000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************读block48电极************\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

    spi_cmd="00100000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************解除模拟全局复位************\n",'custom_font')
    time.sleep(0.1)

def Stim(console_output):
    #ELE11 实测无问题
    console_output.tag_config('custom_font', font=('Arial', 12), foreground='blue')
    #//刺激器DAC parameter: OFF_STIM + CH[1:0] + AMP_X50 + comp_en + Pol[1:0] + STIM_AMP[8:0]
    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

    spi_cmd = "000110_00110000_01_0011100111111110"  
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************补偿************\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

    spi_cmd = "000110_00110000_01_0011000111111110"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************关闭补偿***********\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

    spi_cmd = "000011_00110000_01_0000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************读CBOK************\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

    spi_cmd = "010010_0011000001_0000_000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************设置CBOK_LOW************\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)
    
    spi_cmd = "000110_00110000_01_0_01_1_0_01_111111111"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************刺激************\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)
def Stim_ELE1(console_output):
    #ELE1 实测无问题
    console_output.tag_config('custom_font', font=('Arial', 12), foreground='blue')
    #//刺激器DAC parameter: OFF_STIM + CH[1:0] + AMP_X50 + comp_en + Pol[1:0] + STIM_AMP[8:0]
    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

    spi_cmd = "000110_00111000_01_0111100111111110"  
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************补偿************\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

    spi_cmd = "000110_00111000_01_0111000111111110"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************关闭补偿***********\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

    spi_cmd = "000011_00111000_01_0000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************读CBOK************\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

    spi_cmd = "010010_0011100001_0000_000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************设置CBOK_LOW************\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)
    
    spi_cmd = "000110_00111000_01_0_11_1_0_01_111111111"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************刺激************\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

def Stim_ELE2(console_output):
    #ELE2 实测无问题
    console_output.tag_config('custom_font', font=('Arial', 12), foreground='blue')
    #//刺激器DAC parameter: OFF_STIM + CH[1:0] + AMP_X50 + comp_en + Pol[1:0] + STIM_AMP[8:0]
    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

    spi_cmd = "000110_00111000_01_0101100111111110"  
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************补偿************\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

    spi_cmd = "000110_00111000_01_0101000111111110"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************关闭补偿***********\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

    spi_cmd = "000011_00111000_01_0000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************读CBOK************\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

    spi_cmd = "010010_0011100001_0000_000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************设置CBOK_LOW************\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)
    
    spi_cmd = "000110_00111000_01_0_10_1_0_01_111111111"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************刺激************\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

def Stim_ELE5(console_output):
    #ELE5 实测无问题
    console_output.tag_config('custom_font', font=('Arial', 12), foreground='blue')
    #//刺激器DAC parameter: OFF_STIM + CH[1:0] + AMP_X50 + comp_en + Pol[1:0] + STIM_AMP[8:0]
    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

    spi_cmd = "000110_00111000_00_0111100111111110"  
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************补偿************\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

    spi_cmd = "000110_00111000_00_0111000111111110"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************关闭补偿***********\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

    spi_cmd = "000011_00111000_00_0000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************读CBOK************\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

    spi_cmd = "010010_0011100000_0000_000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************设置CBOK_LOW************\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)
    
    spi_cmd = "000110_00111000_00_0_11_1_0_10_111111111"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************刺激************\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

def Stim_ELE6(console_output):
    #ELE6 实测无问题
    console_output.tag_config('custom_font', font=('Arial', 12), foreground='blue')
    #//刺激器DAC parameter: OFF_STIM + CH[1:0] + AMP_X50 + comp_en + Pol[1:0] + STIM_AMP[8:0]
    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

    spi_cmd = "000110_00111000_00_0101100111111110"  
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************补偿************\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

    spi_cmd = "000110_00111000_00_0101000111111110"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************关闭补偿***********\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

    spi_cmd = "000011_00111000_00_0000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************读CBOK************\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

    spi_cmd = "010010_0011100000_0000_000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************设置CBOK_LOW************\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)
    
    spi_cmd = "000110_00111000_00_0_10_1_0_01_111111111"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************刺激************\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

def Stim_ELE11(console_output):
    #ELE11 实测无问题
    console_output.tag_config('custom_font', font=('Arial', 12), foreground='blue')
    #//刺激器DAC parameter: OFF_STIM + CH[1:0] + AMP_X50 + comp_en + Pol[1:0] + STIM_AMP[8:0]
    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

    spi_cmd = "000110_00110000_01_0011100111111110"  
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************补偿************\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

    spi_cmd = "000110_00110000_01_0011000111111110"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************关闭补偿***********\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

    spi_cmd = "000011_00110000_01_0000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************读CBOK************\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

    spi_cmd = "010010_0011000001_0000_000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************设置CBOK_LOW************\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)
    
    spi_cmd = "000110_00110000_01_0_01_1_0_01_111111111"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************刺激************\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

def Stim_ELE12(console_output):
    console_output.tag_config('custom_font', font=('Arial', 12), foreground='blue')
    #//刺激器DAC parameter: OFF_STIM + CH[1:0] + AMP_X50 + comp_en + Pol[1:0] + STIM_AMP[8:0]
    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

    spi_cmd = "000110_00110000_01_0001100111111110"  
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************补偿************\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

    spi_cmd = "000110_00110000_01_0001000111111110"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************关闭补偿***********\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

    spi_cmd = "000011_00110000_01_0000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************读CBOK************\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

    spi_cmd = "010010_0011000001_0000_000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************设置CBOK_LOW************\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)
    
    spi_cmd = "000110_00110000_01_0_00_1_0_01_111111111"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************刺激************\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

def Stim_ELE13(console_output):
    #ELE13 实测无问题
    console_output.tag_config('custom_font', font=('Arial', 12), foreground='blue')
    #//刺激器DAC parameter: OFF_STIM + CH[1:0] + AMP_X50 + comp_en + Pol[1:0] + STIM_AMP[8:0]
    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

    spi_cmd = "000110_00110000_00_0111100111111110"  
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************补偿************\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

    spi_cmd = "000110_00110000_00_0111000111111110"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************关闭补偿***********\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

    spi_cmd = "000011_00110000_00_0000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************读CBOK************\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

    spi_cmd = "010010_0011000000_0000_000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************设置CBOK_LOW************\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)
    
    spi_cmd = "000110_00110000_00_0_11_1_0_01_111111111"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************刺激************\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

def Stim_ELE14(console_output):
    console_output.tag_config('custom_font', font=('Arial', 12), foreground='blue')
    #//刺激器DAC parameter: OFF_STIM + CH[1:0] + AMP_X50 + comp_en + Pol[1:0] + STIM_AMP[8:0]
    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

    spi_cmd = "000110_00110000_00_0101100111111110"  
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************补偿************\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

    spi_cmd = "000110_00110000_00_0101000111111110"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************关闭补偿***********\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

    spi_cmd = "000011_00110000_00_0000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************读CBOK************\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

    spi_cmd = "010010_0011000000_0000_000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************设置CBOK_LOW************\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)
    
    spi_cmd = "000110_00110000_00_0_10_1_0_10_111111111"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************刺激************\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)





def Stim_Multi(console_output):
    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)
    
    spi_cmd = "000110_00111000_01_1_11_1_0_01_111111111"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************刺激配置ELE1************\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)
    
    spi_cmd = "000110_00111000_00_1_11_1_0_01_111111111"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************刺激配置ELE5************\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

    spi_cmd = "000110_00110000_01_1_01_1_0_01_111111111"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************刺激配置ELE11************\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)
######################################
    spi_cmd = "000110_00110000_00_0111100111111110"  
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************补偿************\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

    spi_cmd = "000110_00110000_00_0111000111111110"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************关闭补偿***********\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

    spi_cmd = "000011_00110000_00_0000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************读CBOK************\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

    spi_cmd = "010010_0011000000_0000_000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************设置CBOK_LOW************\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "000110_00110000_00_1_11_1_0_01_111111111"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************刺激配置ELE13************\n",'custom_font')
    time.sleep(0.1)


    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

    spi_cmd = "000110_00110000_00_0_11_1_0_01_111111111"  
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************刺激配置ELE13************\n",'custom_font')
    time.sleep(0.1)


def Stim_ELE16(console_output):
    #ELE13 实测无问题
    console_output.tag_config('custom_font', font=('Arial', 12), foreground='blue')
    #//刺激器DAC parameter: OFF_STIM + CH[1:0] + AMP_X50 + comp_en + Pol[1:0] + STIM_AMP[8:0]
    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

    spi_cmd = "000110_00110000_00_0001100111111110"  
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************补偿************\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

    spi_cmd = "000110_00110000_00_0001000111111110"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************关闭补偿***********\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

    spi_cmd = "000011_00110000_00_0000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************读CBOK************\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)

    spi_cmd = "010010_0011000000_0000_000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************设置CBOK_LOW************\n",'custom_font')
    time.sleep(0.1)

    spi_cmd = "00000000000000000000000000000000"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"dummy\n")
    time.sleep(0.1)
    
    spi_cmd = "000110_00110000_00_0_00_1_0_01_111111111"
    single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"*************刺激************\n",'custom_font')
    time.sleep(0.1)

    



def Set_global_gain_high(console_output):
    code = "000100"
    for adder_num in range(64):  # 0 to 63 (6-bit)
        adder = "00" + format(adder_num, '06b')  # 8-bit: '00' + 6-bit adder
        for channel_num in range(4):  # 0 to 3 (2-bit)
            channel = format(channel_num, '02b')
            data = "0000000001011110"
            spi_cmd = code + adder + channel + data
            single_TCP(spi_cmd, console_output)
            spi_cmd = "00000000000000000000000000000000"
            single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"set global gain high!!\n")


def Set_global_gain_low(console_output):
    code = "000100"
    for adder_num in range(64):  # 0 to 63 (6-bit)
        adder = "00" + format(adder_num, '06b')  # 8-bit: '00' + 6-bit adder
        for channel_num in range(4):  # 0 to 3 (2-bit)
            channel = format(channel_num, '02b')
            data = "0000000001111110"
            spi_cmd = code + adder + channel + data
            single_TCP(spi_cmd, console_output)
            spi_cmd = "00000000000000000000000000000000"
            single_TCP(spi_cmd,console_output)
    console_output.insert(tk.END, f"set global gain high!!\n")

