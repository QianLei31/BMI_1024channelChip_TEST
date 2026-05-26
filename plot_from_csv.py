import pandas as pd
import matplotlib.pyplot as plt

# 读取CSV文件
file_path = r'c:\Users\29688\Desktop\RigolDS8.csv'  # 替换为你的CSV文件路径
df = pd.read_csv(file_path)
start_offset=0
data_end=1000001
# 提取列数据
x = df.iloc[:, 0][start_offset:data_end]  # 提取第一列作为x
print(len(x))
y=df.iloc[:, 1][start_offset:data_end]

fig = plt.figure()
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False
plt.plot(x, y)
# 设置坐标轴标签
plt.xlabel('时间 (s)',fontsize=14,fontweight='bold')
plt.ylabel('电极电压 (V)',fontsize=14,fontweight='bold')
plt.show()