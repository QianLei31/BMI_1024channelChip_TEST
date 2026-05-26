import socket
import binascii
from matplotlib.offsetbox import AnchoredText
import matplotlib.pyplot as plt
import os
from numpy.linalg import norm
import numpy as np
from mpl_toolkits.mplot3d import Axes3D
from matplotlib.gridspec import GridSpec
from mpl_toolkits.axes_grid1 import make_axes_locatable
from matplotlib.ticker import AutoLocator, AutoMinorLocator
from scipy.ndimage import gaussian_filter
from matplotlib.colorbar import Colorbar
from collections import deque
from fun_cal_sndr import cal_sndr
from fun_cal_snr import cal_snr
from test_fftclean import fft_clean
########################################USER CONFIG############################################

fs=10000000/80/12
fb=fs//2
cal=1  #1:sndr 2:snr 3:fft_clean
ADC_bits=12
fft_points=65536
readbytes_offset=10000 #read data from initial_offset
BYTES_DATA_POINTS=4 
plot_real=1
readfile_offset=0 # read offset from the last file
# 1102_1817 7uVrms
dir = r'd:\ADC_data'
subdirectories = [os.path.join(dir, d) for d in os.listdir(dir) if os.path.isdir(os.path.join(dir, d))]
subdirectories.sort(key=lambda x: os.path.getctime(x), reverse=True)
readdir = subdirectories[readfile_offset]
if plot_real==0:
    plotdir = r"d:\ADC_data\1102_1634"
else:
    plotdir=readdir
plotdir=os.path.join(plotdir,'channel')
strPathRead = plotdir



plotchannel_list=np.linspace(0,255,256,dtype=int)
sortlist=plotchannel_list
excluded_channels=[118, 155, 177,4, 5, 7, 16, 17, 18, 19, 20, 21, 22, 23, 29, 36, 37, 38, 40, 41, 42, 43, 52, 53, 54, 55, 56, 57, 58, 59, 73, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 100, 101, 103, 116, 119, 148, 153, 154, 171, 185, 186, 187, 192, 193, 194, 195, 201, 202, 203, 212, 213, 214, 215, 221, 244, 245, 246]
plotchannel_list = np.setdiff1d(plotchannel_list, excluded_channels)

str_file_read= os.path.join(strPathRead, "NL_channel_191.bin")
print(str_file_read)
#str_file_read=r"d:\testchip_results\NSSAR_v1\1101_0947\ADC_DATA.bin"
################################################################################################

def process_data(data):
    values = np.zeros(len(data)//BYTES_DATA_POINTS)
    for i in range(0, len(data), BYTES_DATA_POINTS):
        values[i//BYTES_DATA_POINTS] = int.from_bytes(data[i:i+BYTES_DATA_POINTS], byteorder='little')
    return values
with open(str_file_read, "rb") as file:
    file.seek(readbytes_offset)
    data=file.read(fft_points*4)
data=process_data(data)/2**ADC_bits*1.8
##################cal_sndr##################

if (cal==1):
    sndr,enob,irn,fin,fft_data,fft_freq,irn_pow,thd= cal_sndr(data,fs,fb,'hann')
    fig,ax=plt.subplots() 
    plt.title("Specrum of the signal")
    plt.xlabel('Frequency/Hz')
    plt.ylabel('AMPLITUDE(dBFS)')
    text_content = f'Freq: {fin:.2f}Hz\nTHD:{thd:.2f}dB\nENOB: {round(enob,2)}bit\nSNDR: {sndr:.2f}dB\nIRN_POWER:{irn_pow:.2f}dB\nIRN:{irn/60:.9f}Vrms'
    text_box = AnchoredText(text_content, loc='upper right')
    text_box.patch.set_boxstyle("round,pad=0.,rounding_size=0.2")
    ax.add_artist(text_box)
    xdata=fft_freq
    ydata=10*np.log10(fft_data)
    line, = plt.semilogx(xdata, ydata)
    line.set_data(xdata, ydata)
    plt.show()
elif (cal==2):
    snr,spectP = cal_snr(data,fb,fs,title='test',log=1)
    plt.show()
elif (cal==3):
    fft_freq, fft_data, sndr, enob, signband_power, sig_power,dc_power = fft_clean(data, fs, 1, 317.73, 4)
    print(sndr, enob, signband_power, sig_power,dc_power)
    fig,ax=plt.subplots() 
    plt.title("Specrum of the signal")
    plt.xlabel('Frequency/Hz')
    plt.ylabel('AMPLITUDE(dBFS)')
    text_content = f'SNDR: {sndr:.2f}dB\nENOB: {round(enob,2)}bit'
    text_box = AnchoredText(text_content, loc='upper right')
    text_box.patch.set_boxstyle("round,pad=0.,rounding_size=0.2")
    ax.add_artist(text_box)
    xdata=fft_freq
    ydata=10*np.log10(fft_data)
    line, = plt.semilogx(xdata, ydata)
    line.set_data(xdata, ydata)
    plt.show()
else:
    [Pxx1,f1] = plt.psd(data,                       # 随机信号
                    NFFT=fft_points,               # 每个窗的长度
                    Fs=fs,                   # 采样频率
                    detrend='mean',          # 去掉均值
                    window=np.hanning(fft_points), # 加汉尼窗
                    noverlap=int(fft_points*3/4),  # 每个窗重叠75%的数据
                    sides='twosided')        # 求双边谱
    plt.xscale('log')
    w=np.hanning(fft_points)


