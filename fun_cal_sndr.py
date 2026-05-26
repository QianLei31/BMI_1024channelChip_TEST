import numpy as np
from numpy.linalg import norm
from scipy import signal
import matplotlib.pyplot as plt
from collections import deque
from matplotlib.offsetbox import AnchoredText
def cal_sndr(data,fs,fb,wintype):
    #data：时间域数据，需要进行频谱分析的信号
    #fs：采样率
    #fb：积分带宽
    #wintype：计算功率谱的窗口类型
    span=5
    AMP=0.01
    # 计算FFT长度
    len_fft=int(round(len(data)))
    # 计算频率分辨率
    resolution = fs / len_fft
    # 计算FFT结果中显示的长度  
    len_fftdisplay=int(round(len(data)/2))
    # 计算频率轴上的频率值
    fft_freq = np.linspace(resolution, round(fs / 2), num=len_fftdisplay)
    # 选择窗函数
    if wintype == 'rect':
        nsig = 1
        win = np.ones(len_fft)
    elif wintype == 'hann':
        nsig = 5
        win = np.hanning(len_fft)
    elif wintype == 'blackman':
        nsig = 5
        win = np.blackman(len_fft)
    elif wintype == 'kaiser':
        nsig = 7
        win = np.kaiser(len_fft, 20)
    # 将输入的时间域数据转换为NumPy数组
    data=np.asarray(data)
    # 计算时间域归一化的数据
    data_norm=data-np.mean(data)
    # 计算FFT结果
    fft_data=(abs(np.fft.fft(np.multiply(data_norm,win)))[0:len_fftdisplay])**2
    fft_freq = np.linspace(resolution, round(fs/2), num=len_fftdisplay)
    # 对fft_data进行标准化
    Sig_max=max(fft_data[span:len_fftdisplay])
    fft_data = fft_data/norm(win)**2/fs
    sigband_bins = 1 + round(fb/resolution)  # 积分频带的FFT点数
    sigband_power = resolution * sum(fft_data[0:sigband_bins-1]) # 积分频带的功率
    Bin = np.argmax(fft_data[span:len_fftdisplay]) + span+1 # 输入信号的FFT点数
    fin=(Bin-1)*resolution # 输入信号的频率
    nsig=1
    sig_power=resolution*sum(fft_data[Bin-nsig:Bin+nsig]) # 输入信号的功率
    dc_win=max(span,int(1/resolution)) # 直流功率窗口的FFT点数
    dc_power=resolution*sum(fft_data[0:span]) # 直流功率
    sndr = np.sqrt(sig_power / (sigband_power - sig_power - dc_power)) # 计算SNDR


    THD_power2=resolution*sum(fft_data[Bin*2-nsig:Bin*2+nsig]) # 谐波的功率
    THD_power3=resolution*sum(fft_data[Bin*3-nsig:Bin*3+nsig]) # 谐波的功率
    THD_power4=resolution*sum(fft_data[Bin*4-nsig:Bin*4+nsig]) # 谐波的功率
    THD_power5=resolution*sum(fft_data[Bin*5-nsig:Bin*5+nsig]) # 谐波的功率
    thd=np.sqrt((THD_power2+THD_power3+THD_power4+THD_power5) / (sig_power))# 计算THD
    thd_db=20 * np.log10(thd)
    sndr_db = 20 * np.log10(sndr)
    enob = (sndr_db - 1.76) / 6.02
    IRN_power=(sigband_power-dc_power)*2 #输入接地，积分带宽内的噪声
    IRN_pwerdb=10*np.log10(IRN_power)
    IRN = np.sqrt(IRN_power)

    return sndr_db,enob,IRN,fin,fft_data,fft_freq,IRN_pwerdb,thd_db



'''
# Example usage:
fbin=7
osr=10
fs=1e6
fb=fs/2/osr
nfft=16384
t=np.array(range(nfft))*(1/fs)
ysig=np.sin(2*np.pi*fbin/nfft*fs*t)
ynoise=0.0001*np.random.randn(nfft)
yout = ysig+ynoise
##################cal_sndr##################
sndr,enob,irn,fin,fft_data,fft_freq= cal_sndr(yout,fs,fb,'hann')
print(sndr,enob,fin)
fig,ax=plt.subplots() 
plt.title("Specrum of the signal")
plt.xlabel('Frequency/Hz')
plt.ylabel('AMPLITUDE(dBFS)')
text_content = f'Freq: {fin:.2f}Hz\nSNDR: {sndr:.2f}dB\nENOB: {round(enob,2)}bit'
text_box = AnchoredText(text_content, loc='upper right')
text_box.patch.set_boxstyle("round,pad=0.,rounding_size=0.2")
ax.add_artist(text_box)
xdata=fft_freq
ydata=10*np.log10(fft_data)
line, = plt.semilogx(xdata, ydata)
line.set_data(xdata, ydata)
plt.show()
'''