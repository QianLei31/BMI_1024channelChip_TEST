import pandas as pd
import matplotlib.pyplot as plt
import os
import numpy as np
from scipy.interpolate import interp1d

# 读取Excel文件
current_directory = os.path.dirname(os.path.realpath(__file__))
file_name = 'TF.xlsx'
file_path = os.path.join(current_directory, file_name)
df = pd.read_excel(file_path)

# 获取X和Y的数据
x_data = df.iloc[:, 0]
y_data = df.iloc[:, 3]

# 使用interp1d创建插值函数
target_gain=30
# 绘制原始数据曲线
plt.plot(x_data, y_data, marker='o', linestyle='-')

plt.title('Transfer Function')  # 替换为你想要的图表标题
plt.xlabel('Frequency/Hz')  # 替换为X轴标签
plt.ylabel('Gain')  # 替换为Y轴标签
plt.xscale('log')

# 显示图例
plt.legend()

# 显示图表
plt.grid(False)
plt.show()
