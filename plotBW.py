import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d

# 原始数据
frequencies = np.array([10,  20,    30,  50,  100,   500   ])
amplitudes = np.array([7.6, 7.06,   5.0,  3.8, 2.4,  0.56])

# 转换为dB参考最大振幅
ref_amplitude = 7.06  # 最大振幅
dB = 20 * np.log10(amplitudes / ref_amplitude)  # dB转换

# 创建插值函数（对数-线性插值）
interp_func = interp1d(np.log10(frequencies), dB, kind='linear', fill_value='extrapolate')

# 生成密集频率点（对数分布）
dense_freq = np.logspace(np.log10(10), np.log10(4000), 10000)
interp_dB = interp_func(np.log10(dense_freq))

# 寻找-3dB交叉点
cross_index = np.where(interp_dB <= -3)[0]
if cross_index.size > 0:
    exact_cross_freq = dense_freq[cross_index[0]]
    exact_cross_dB = interp_dB[cross_index[0]]
else:
    exact_cross_freq = None

# 可视化
plt.figure(figsize=(10,6))
plt.semilogx(frequencies, dB, 'ro', label='Origin')
plt.semilogx(dense_freq, interp_dB, 'b-', label='Interp', linewidth=1.5)
if exact_cross_freq:
    plt.scatter(exact_cross_freq, exact_cross_dB, s=100, c='green', 
                label=f'-3dB: {exact_cross_freq:.1f}Hz')
plt.axhline(-3, color='gray', linestyle='--')
plt.xlabel('Frequency (Hz)')
plt.ylabel('Amplitude (dB)')
plt.grid(True, which='both', linestyle='--')
plt.legend()
plt.show()

# 输出结果
if exact_cross_freq:
    print(f"精确-3dB频率: {exact_cross_freq:.2f} Hz")
else:
    print("未发现-3dB交叉点")