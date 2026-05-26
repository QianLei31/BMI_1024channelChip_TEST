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
########################################USER CONFIG############################################

plot_real=0
fs=10000000/80/12
fb=fs//2
cal=1
ADC_bits=12
fft_points=65536
readfile_offset=0 # read offset from time sort
#取float向上整数部分
readbytes_offset=156000 #read data from initial_offset
BYTES_DATA_POINTS=4 
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

str_file_read=r"d:\testchip_results\NL\ADC_DATA_stim_rec.bin"
str_file_read1=r"d:\testchip_results\NL\ADC_DATA_rec_stim.bin"
print(str_file_read)
################################################################################################

def process_data(data):
    values = np.zeros(len(data)//BYTES_DATA_POINTS)
    for i in range(0, len(data), BYTES_DATA_POINTS):
        values[i//BYTES_DATA_POINTS] = int.from_bytes(data[i:i+BYTES_DATA_POINTS], byteorder='little')
    return values
with open(str_file_read, "rb") as file:
    file.seek(0)
    data=file.read()
data_d=process_data(data)/2**(ADC_bits)*1.8
print("Data length: ", len(data_d))

with open(str_file_read1, "rb") as file:
    file.seek(6000)
    data=file.read()
data_d1=process_data(data)/2**(ADC_bits)*1.8
print("Data length: ", len(data_d1))
data_total=np.concatenate((data_d1,data_d))
##################cal_sndr##################
time_x=len(data_total)/fs
fig=plt.figure()
#plt.rcParams['font.sans-serif'] = ['SimHei']
#plt.rcParams['axes.unicode_minus'] = False
#plt.title("关闭/打开刺激开关时记录信号",fontsize=20,fontweight='bold')
plt.xlabel("Time",fontsize=14,fontweight='bold',fontname='Times New Roman')
plt.ylabel("Voltage",fontsize=14,fontweight='bold',fontname='Times New Roman')
plt.xticks(fontsize=10, fontname='Times New Roman', fontweight='bold')
plt.yticks(fontsize=10, fontname='Times New Roman', fontweight='bold')
plt.plot(np.arange(0,time_x,1/fs),data_total)
save_path = r'd:\testchip_results\NL'
plt.savefig(os.path.join(save_path, 'STIM_REC.svg'), format='svg')  
plt.show()
