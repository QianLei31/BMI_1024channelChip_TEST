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
readfile_offset=21 # read offset from time sort
readbytes_offset=10000 #read data from initial_offset
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
str_file_read= os.path.join(strPathRead, "NL_channel_195.bin")
print(str_file_read)
#str_file_read=r"d:\testchip_results\NSSAR_v1\1101_0947\ADC_DATA.bin"
################################################################################################

def getADC_bits(data_recv, resolution_bits):
    # 计算分辨率
    resolution = 2 ** resolution_bits
    data = data_recv % resolution
    # 统计每个数出现的次数
    data_min = np.min(data)
    data_max = np.max(data)
    x = np.arange(data_min, data_max + 1)
    y = np.zeros(len(x), dtype=int)
    for z in range(len(x)):
        y[z] = np.sum(data == x[z])
    
    # 绘制条形图
    plt.bar(x, y)
    plt.rcParams['font.sans-serif'] = ['SimHei']  # 指定使用中文字体

    plt.xlabel("12bit ADC 数字码流分布")  # 添加横轴标签
    plt.ylabel("counts")   # 添加纵轴标签
    plt.title("12 bit SAR ADC resolution")  # 添加图表标题
    

    nonzero_counts = np.count_nonzero(y)
    plt.text(data_max, 50, f'Nonzero steps: {nonzero_counts}', ha='right', va='bottom')


def process_data(data):
    values = np.zeros(len(data)//BYTES_DATA_POINTS)
    for i in range(0, len(data), BYTES_DATA_POINTS):
        values[i//BYTES_DATA_POINTS] = int.from_bytes(data[i:i+BYTES_DATA_POINTS], byteorder='little')
    return values

with open(str_file_read, "rb") as file:
    file.seek(readbytes_offset)
    data=file.read()
getADC_bits(process_data(data), 12)
plt.show()


