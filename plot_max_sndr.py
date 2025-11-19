import socket
import binascii
from matplotlib.offsetbox import AnchoredText
import matplotlib.pyplot as plt
import os
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

############################################  USER DEFINE  ###################################
indicator=2 # 1: sndr 2:irn
plot_real=1 
fs=10000000/80/12
fb=fs//2
cal=1  #1:sndr 2:snr 3:fft_clean
time_scale=1
delta=1
ADC_bits=12
BYTES_DATA_POINTS=4 
chunk_data_size=int(fs*4*delta*time_scale)
deltafft=chunk_data_size//40
readfile_offset=10 # read offset from time sort
readbytes_offset=0
dir = r'd:\ADC_data'
plot_dir='1022_1400'
fft_points=65536
subdirectories = [os.path.join(dir, d) for d in os.listdir(dir) if os.path.isdir(os.path.join(dir, d))]
subdirectories.sort(key=lambda x: os.path.getctime(x), reverse=True)
readdir = subdirectories[readfile_offset]
if plot_real==0:
    plotdir = r"d:\ADC_data\1102_1634"
else:
    plotdir=readdir
plotdir=os.path.join(plotdir,'channel')
strPathRead = plotdir
str_file_read= os.path.join(strPathRead, "NL_channel_195.bin")
print(str_file_read)
max_enob = -float("inf")
min_irn = float("inf")
############################################  DEFINE END   ########################################


best_sndr_index = 0
best_irn_index=0
def process_data(data):
    values = np.zeros(len(data)//BYTES_DATA_POINTS)
    for i in range(0, len(data), BYTES_DATA_POINTS):
        values[i//BYTES_DATA_POINTS] = int.from_bytes(data[i:i+BYTES_DATA_POINTS], byteorder='little')
    return values
with open(str_file_read, "rb") as file:
    file.seek(readbytes_offset)
    data=file.read()
    if len(data)<fft_points*4:
        print('file too short')
        exit()
data=np.array(process_data(data))/2**ADC_bits*1.8

##################cal_sndr##################
for i in range(0, len(data) - fft_points + 1, deltafft):  # 每次增加 delta
    segment = data[i:i + fft_points]
    sndr,enob,irn,fin,fft_data,fft_freq,irn_pow= cal_sndr(segment,fs,fb,'blackman')
    print(irn)
    if enob > max_enob:
        max_enob = enob
        best_sndr_index = i
    if irn < min_irn:
        min_irn = irn
        best_irn_index=i
print(best_sndr_index,'best_index')
print(best_irn_index,'best_irn_index')

if indicator==1:
    best_index=best_sndr_index
elif indicator==2:
    best_index=best_irn_index
if (cal==1):
    sndr,enob,irn,fin,fft_data,fft_freq,irn_pow= cal_sndr(data[best_index:best_index + fft_points],fs,fb,'blackman')
    fig,ax=plt.subplots() 
    plt.title("Specrum of the signal")
    plt.xlabel('Frequency/Hz')
    plt.ylabel('AMPLITUDE(dBFS)')
    text_content = f'Freq: {fin:.2f}Hz\nSNDR: {sndr:.2f}dB\nIRN_POWER:{irn_pow:.2f}\nIRN:{irn:.9f}\nENOB: {round(enob,2)}bit'
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
else :
    fft_freq, fft_data, sndr, enob, signband_power, sig_power,dc_power = fft_clean(data, fs, 1, 123.5, 4)
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


