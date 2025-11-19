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
import warnings
import seaborn as sns
from scipy.stats import norm

# Configuration
fs = 10000000/80/12
fb = fs//2
cal = 1  # 1:sndr 2:snr 3:fft_clean
ADC_bits = 12
fft_points = 65536
readbytes_offset = 10000  # read data from initial_offset
BYTES_DATA_POINTS = 4 
plot_real = 0
readfile_offset = 0  # read offset from the last file

# Directory setup
dir = r'd:\ADC_data'
subdirectories = [os.path.join(dir, d) for d in os.listdir(dir) if os.path.isdir(os.path.join(dir, d))]
subdirectories.sort(key=lambda x: os.path.getctime(x), reverse=True)
readdir = subdirectories[readfile_offset]
if plot_real == 0:
    plotdir = r"d:\ADC_data\1102_1634"
    plotdir = r"d:\ADC_data\0513_1736"  #rst
    plotdir = r"d:\ADC_data\0403_1708"  
else:
    plotdir = readdir
plotdir = os.path.join(plotdir, 'channel')
strPathRead = plotdir

# Channel setup
plotchannel_list = np.linspace(0, 255, 256, dtype=int)
sortlist = plotchannel_list
excluded_channels = [30, 249,6, 48, 117, 128, 149, 150, 152, 169, 170, 176, 200, 206, 224, 227, 230, 231, 232, 233, 234, 235, 237, 240, 241, 242, 243, 247, 248,118, 155, 177, 4, 5, 7, 16, 17, 18, 19, 20, 21, 22, 23, 29, 36, 37, 38, 40, 41, 42, 43, 52, 53, 54, 55, 56, 57, 58, 59, 73, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 100, 101, 103, 116, 119, 148, 153, 154, 171, 185, 186, 187, 192, 193, 194, 195, 201, 202, 203, 212, 213, 214, 215, 221, 244, 245, 246]
plotchannel_list = np.setdiff1d(plotchannel_list, excluded_channels)


def process_data(data):
    values = np.zeros(len(data)//BYTES_DATA_POINTS)
    for i in range(0, len(data), BYTES_DATA_POINTS):
        values[i//BYTES_DATA_POINTS] = int.from_bytes(data[i:i+BYTES_DATA_POINTS], byteorder='little')
    return values

# Create a figure for all FFT plots
plt.figure(figsize=(12, 8))

# Process each channel
problem_channels = []  # To store channels with calculation problems
valid_channels = []    # To store successfully processed channels
low_amplitude_channels = []
all_irn = []
valid_irn_channels = []


for channel_index in plotchannel_list:
    file_path = os.path.join(plotdir, f'NL_channel_{channel_index}.bin')
    
    try:
        with open(file_path, "rb") as file:
            file.seek(readbytes_offset)
            data = file.read(fft_points * BYTES_DATA_POINTS)
        
        # Process data and convert to voltage
        data = process_data(data) / 2**ADC_bits * 1.8
        
        # Calculate FFT and other metrics with warning handling
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")  # Show all warnings
            try:
                sndr, enob, irn, fin, fft_data, fft_freq, irn_pow, thd = cal_sndr(data, fs, fb, 'hann')
                all_irn.append(irn*1e6)  # 收集IRN数据
                valid_irn_channels.append(channel_index)
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")  # 屏蔽log计算的警告
                    db_data = 10*np.log10(fft_data)
                    mean_amplitude = np.nanmean(db_data)  # 处理NaN情况

                    if mean_amplitude < -300:
                        low_amplitude_channels.append(channel_index)
                
                # Check if we got any warnings
                if w:
                    problem_channels.append((channel_index, [str(warn.message) for warn in w]))
                    print(f"Warning in channel {channel_index}:")
                    for warning in w:
                        print(f"  {warning.message}")
                    continue  # Skip plotting for this channel
                
                # If no warnings, proceed with plotting
                plt.semilogx(fft_freq, 10*np.log10(fft_data), label=f'Ch {channel_index} (SNDR: {sndr:.1f}dB)')
                valid_channels.append(channel_index)
                
            except Exception as e:
                problem_channels.append((channel_index, [str(e)]))
                print(f"Exception in channel {channel_index}: {str(e)}")
                continue
        
    except Exception as e:
        problem_channels.append((channel_index, [f"File error: {str(e)}"]))
        print(f"File error for channel {channel_index}: {str(e)}")
        continue

# Add plot decorations
plt.title("FFT Spectrum of Valid Channels")
plt.xlabel('Frequency (Hz)')
plt.ylabel('Amplitude (dBFS)')
plt.grid(True, which="both", ls="-")

# Add legend (might be crowded with many channels)
plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', borderaxespad=0., fontsize='small')
plt.tight_layout()

# Print summary of processing results
print("\nProcessing Summary:")
print(f"Total channels attempted: {len(plotchannel_list)}")
print(f"Successfully processed: {len(valid_channels)}")
print(f"Channels with problems: {len(problem_channels)}")

# 单独打印问题通道列表和详细信息
if problem_channels:
    # 按通道号排序
    problem_channels_sorted = sorted(problem_channels, key=lambda x: x[0])
    
    # 提取并打印纯通道号列表
    problem_numbers = [ch for ch, _ in problem_channels_sorted]
    print("\nProblem channel numbers:")
    print(problem_numbers)
    
    # 打印详细错误信息
    print("\nDetailed errors:")
    for channel, errors in problem_channels_sorted:
        print(f"\nChannel {channel} errors:")
        for error in errors:
            print(f"  • {error}")



# 在结果汇总部分添加输出
print("\nProcessing Summary:")
print(f"Total channels attempted: {len(plotchannel_list)}")
print(f"Successfully processed: {len(valid_channels)}")
print(f"Channels with problems: {len(problem_channels)}")
print(f"Channels with amplitude mean < -300 dBFS: {len(low_amplitude_channels)}")

if low_amplitude_channels:
    print("\nLow amplitude channels (mean < -300 dBFS):")
    print(sorted(low_amplitude_channels))
else:
    print("\nNo channels with amplitude mean < -300 dBFS")

if len(all_irn) > 0:
    # 统计分析
    irn_array = np.array(all_irn)/60  # 这里已经是μVrms单位,等效到输入
    mean_val = np.mean(irn_array)
    std_val = np.std(irn_array)
    min_val = np.min(irn_array)
    max_val = np.max(irn_array)
    
    # 打印统计结果
    print("\nIRN Statistical Analysis:")
    print(f"Valid channels: {len(irn_array)}")
    print(f"Mean ± Std: {mean_val:.3f} ± {std_val:.3f} μVrms")
    print(f"Min/Max: [{min_val:.3f}, {max_val:.3f}] μVrms")
    
    # 绘制分布图
    plt.figure(figsize=(10, 6))
    
    # 绘制直方图（显示通道数量）
    ax = sns.histplot(irn_array, kde=False, stat="count",  # 关键修改点
                     bins=20, color='steelblue', alpha=0.7,
                     edgecolor='white', linewidth=0.5)
    
    # 可选：添加通道数标注
    for rect in ax.patches:
        height = rect.get_height()
        if height > 0:
            ax.annotate(f'{int(height)}',
                        xy=(rect.get_x()+rect.get_width()/2, height),
                        xytext=(0, 3),  # 3 points vertical offset
                        textcoords="offset points",
                        ha='center', va='bottom', fontsize=8)
    
    # 移除原正态分布拟合（因单位不匹配）
    plt.title(f"IRN Distribution (N={len(irn_array)} Channels)")
    plt.xlabel("IRN (μVrms)")
    plt.ylabel("Number of Channels")  # 纵坐标标签修改
    plt.grid(True, alpha=0.3)
    
    # 更新统计信息框（保持原统计信息）
    textstr = '\n'.join([
        f'Channels: {len(irn_array)}',
        f'Mean: {mean_val:.1f} μVrms',
        f'Std: {std_val:.1f} μVrms',
        f'Range: [{min_val:.1f}, {max_val:.1f}]'
    ])
    props = dict(boxstyle='round', facecolor='white', alpha=0.8)
    ax.text(0.95, 0.95, textstr, transform=ax.transAxes,
            verticalalignment='top', horizontalalignment='right',
            bbox=props)
    
    plt.tight_layout()
    plt.show()
    
else:
    print("\nNo valid IRN data for analysis")