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

########################################USER CONFIG############################################
D=[1,6,14,30,62,126,254,510]#x坐标
IDAC=[2.8,2.9,4,6.4,11.1,20.2,38.3,73.9]#x坐标

################################################################################################
fig=plt.figure()
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False
plt.xlabel("9bit 控制码",fontsize=14,fontweight='bold')
plt.ylabel("刺激器输出电流/微安",fontsize=14,fontweight='bold')
plt.xticks(fontsize=10, fontname='Times New Roman', fontweight='bold')
plt.yticks(fontsize=10, fontname='Times New Roman', fontweight='bold')
# 绘制散点图
plt.scatter(D, IDAC, color='r', label='输出电流/微安')

# 绘制曲线
plt.plot(D, IDAC, color='b', label='输出电流拟合曲线')

plt.legend(loc='upper left')
save_path = r'd:\testchip_results\NL'
plt.savefig(os.path.join(save_path, 'STIM_DAC.svg'), format='svg')
plt.show()