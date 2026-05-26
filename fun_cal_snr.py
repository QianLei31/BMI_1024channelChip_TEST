import matplotlib.pyplot as plt
import numpy as np
from numpy import sin, pi
def cal_snr(x,fb,fs,title='',log=1):
    dc=np.mean(x)
    for i in range(len(x)):
        x[i]=x[i]-dc
    w=np.hanning(len(x))
    z=np.fft.fft(x*w)
    #z=np.fft.fft(x)
    print("Number of points in FFT:",len(z))
    print("Bandwidth:",fb)
    timestep=1/fs
    freq=[]
    for i in range(len(z)):
        freq.append(i/timestep/len(z))
    #Span of the input frequency on each side
    span=5
    signal=max(np.abs(z[span-1:int(fb*len(z)*timestep)]))
    print("signal",signal)
    #plt.semilogx(freq[1:int(BW*len(z)*timestep)],20*np.log10(np.abs(z[1:int(BW*len(z)*timestep)])/signal))
    if(log):
        plt.semilogx(freq[span:int(len(z)/2)],20*np.log10(np.abs(z[span:int(len(z)/2)])/signal))
    else:
        plt.plot(freq[0:int(len(z)/2)],20*np.log10(np.abs(z[0:int(len(z)/2)])/signal))
    plt.xlabel("Frequency/Hz")
    plt.ylabel("Magnitude/dB")
    plt.ylim([-120,10])
    plt.yticks(range(-120,10,20))
    #snr
    total=0
    print("signal",signal)
    pos_fin=np.where(np.abs(z[1:int(fb*len(z)*timestep)])==signal)
    print("pos_fin",pos_fin[0][0]+1)
    print("pos_bw",int(fb*len(z)/fs))
    fin=(pos_fin[0][0]+1)/timestep/len(z)
    print("fin",fin)
    #detemine power spectrum
    spectP=np.abs(z)**2
    #extract overall signal power
    Ps=0
    for i in range(pos_fin[0][0]+1-span,pos_fin[0][0]+1+span):
        Ps+=spectP[i]
        print("i",i)
    Ptotal=0
    for i in range(span,int(fb*len(z)/fs)):
        Ptotal+=spectP[i]
    print("Ps",Ps)
    print("Ptotal",Ptotal)
    #print(spectP[0:100])
    snr=10*np.log10(Ps/(Ptotal-Ps))
    print("snr",snr)
    plt.text(fin,0.025,"SNR: "+str(snr)+"dB")
    plt.title(title)
    #plt.savefig("D:\\EIT\\DAC\\simulation1\\"+title+".png")
    return snr



'''
fbin=7
osr=10
fs=1e6
nfft=16384
t=np.array(range(nfft))*(1/fs)
ysig=np.sin(2*np.pi*fbin/nfft*fs*t)
ynoise=0.0001*np.random.randn(nfft)
yout = ysig+ynoise
snr,spectP = cal_snr(yout,fs/2/osr,fs,title='test',log=1)
plt.show()
'''