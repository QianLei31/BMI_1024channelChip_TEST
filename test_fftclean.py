import numpy as np
from numpy import sin, pi
from scipy import signal
def fft_clean(data_time, fs, num_fftavg, sin_freq, psd_window):
    data_time = np.asarray(data_time)
    # divide the time-domain data
    len_fft = int(round(len(data_time)/num_fftavg))
    avgdata = sum(data_time)/float(len(data_time))
    data_norm = data_time-avgdata
    len_fftdisplay = int(round(len_fft/2))

    fft_data = np.array([0]*(len_fftdisplay))
    ffttemp = np.array([0]*(len_fftdisplay))
    # w = signal.flattop(len_fft-1)    these are the windows
    # w=1
    w = signal.blackmanharris(len_fft-1, sym=False)
    for ii in range(num_fftavg):
        ffttemp = abs(np.fft.fft(np.multiply(data_norm[ii*len_fft:(ii+1)*len_fft-1], w)))[
            0:len_fftdisplay]  # we only use half the data
#        ffttemp=abs(np.fft.fft(data_norm[ii*len_fft:(ii+1)*len_fft-1]))[0:len_fftdisplay]
        fft_data = fft_data+(ffttemp)**2
#    fft_data=fft_data/num_fftavg/(len_fft**2)
#    fft_data=fft_data/num_fftavg/(len_fft)/fs
    # why divided by lenth of data? scale?
    fft_data = fft_data/num_fftavg/(len_fftdisplay)
    resolution = fs/len_fft
    # we can also use np.fft.fft_freq
    fft_freq = np.linspace(resolution, round(fs/2), num=len_fftdisplay)
    osr = 1
    fres = fs/len_fft  # bin width for frequency resolution
    sigband_bins = 1+round((fs/(2*osr))/fres)
    # sigband_bins=1+round(50000/fres)
    sigband_power = fres*sum(fft_data[psd_window:sigband_bins])
    sig_bin = 1+round(sin_freq/fres)
    sig_bin_min = max(1, sig_bin-psd_window)
    sig_bin_max = sig_bin+psd_window
    sig_power = fres*sum(fft_data[sig_bin_min:sig_bin_max])
    dc_power = fres*sum(fft_data[psd_window:round(1/fres)])
    sndr = np.sqrt(sig_power/(sigband_power-sig_power-dc_power))
    sndr_db = 20*np.log10(sndr)
    enob = (sndr_db-1.76)/6.02
    return (fft_freq.tolist(), fft_data.tolist(), sndr_db, enob, sigband_power, sig_power, dc_power)



'''
fbin=21
osr=10
fs=1e6
fb=fs/2/osr
nfft=4096
t=np.array(range(nfft))*(1/fs)
ysig=np.sin(2*np.pi*fbin/nfft*fs*t)
ynoise=0.0001*np.random.randn(nfft)
yout = ysig+ynoise
fft_freq, fft_data, sndr_db, enob, signband_power, sig_power,dc_power = fft_clean(yout, fs, 1, 5126, 8)
print(sndr_db, enob, signband_power, sig_power,dc_power)
'''