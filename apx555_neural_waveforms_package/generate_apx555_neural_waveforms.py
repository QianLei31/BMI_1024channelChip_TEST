import numpy as np
from pathlib import Path
import math, wave, struct, json

def write_wav_24bit(path, x, fs):
    x = np.asarray(x, dtype=np.float64)
    x = np.clip(x, -0.999999, 0.999999)
    ints = np.round(x * (2**23 - 1)).astype(np.int32)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(3)
        wf.setframerate(fs)
        frames = bytearray()
        for val in ints:
            if val < 0:
                val += 1 << 24
            frames.extend(struct.pack("<I", val)[0:3])
        wf.writeframes(frames)

def save_csv(path, y, fs):
    with open(path, "w", encoding="utf-8") as f:
        f.write("time_s,normalized_value\n")
        for i, v in enumerate(y):
            f.write(f"{i/fs:.10e},{v:.10e}\n")

def rms(x):
    return float(np.sqrt(np.mean(np.asarray(x)**2)))

def normalize_peak(x, peak=0.98):
    m = float(np.max(np.abs(x)))
    return x / m * peak if m > 0 else x

def one_pole_filter(x, fc, fs, mode="lowpass"):
    alpha = math.exp(-2 * math.pi * fc / fs)
    y = np.zeros_like(x)
    if mode == "lowpass":
        for i in range(1, len(x)):
            y[i] = (1 - alpha) * x[i] + alpha * y[i-1]
        return y
    if mode == "highpass":
        return x - one_pole_filter(x, fc, fs, mode="lowpass")
    raise ValueError("mode must be lowpass or highpass")

def bandlimit_lfp_noise(fs, n, f_low=1.0, f_high=300.0, rng=None):
    rng = rng or np.random.default_rng()
    freqs = np.fft.rfftfreq(n, d=1/fs)
    amp = np.zeros_like(freqs)
    mask = (freqs >= f_low) & (freqs <= f_high)
    amp[mask] = 1 / np.sqrt(np.maximum(freqs[mask], f_low))
    phase = rng.uniform(0, 2*np.pi, len(freqs))
    spec = amp * (np.cos(phase) + 1j*np.sin(phase))
    spec[0] = 0
    y = np.fft.irfft(spec, n=n)
    return y / (np.std(y) + 1e-30)

def spike_template(fs, neg_width_ms=0.28, pos_width_ms=0.45, sep_ms=0.42, tail_width_ms=0.75):
    win_ms = 2.4
    tt = np.arange(int(win_ms * 1e-3 * fs)) / fs
    center = 0.75e-3
    neg = -1.00 * np.exp(-0.5 * ((tt - center) / (neg_width_ms*1e-3))**2)
    pos = +0.45 * np.exp(-0.5 * ((tt - (center + sep_ms*1e-3)) / (pos_width_ms*1e-3))**2)
    tail = -0.12 * np.exp(-0.5 * ((tt - (center + 1.12e-3)) / (tail_width_ms*1e-3))**2)
    w = neg + pos + tail
    w = w - np.mean(w)
    return w / abs(np.min(w))

def generate_spike_train(fs, duration, firing_rate_hz=20, refractory_ms=2.0, rng=None):
    rng = rng or np.random.default_rng()
    times = []
    time = 0.05
    refractory = refractory_ms * 1e-3
    while time < duration - 0.05:
        time += max(rng.exponential(1 / firing_rate_hz), refractory)
        if time < duration - 0.05:
            times.append(time)
    return np.array(times)

def add_spikes(fs, n, spike_times, template, amp_mean=1.0, amp_sigma=0.12, rng=None):
    rng = rng or np.random.default_rng()
    y = np.zeros(n)
    L = len(template)
    for st in spike_times:
        idx = int(round(st * fs))
        if idx < 0 or idx + L >= n:
            continue
        amp = max(0.35, rng.normal(amp_mean, amp_sigma))
        y[idx:idx+L] += amp * template
    return y

def main():
    out_dir = Path("apx555_neural_waveforms")
    out_dir.mkdir(exist_ok=True)
    fs = 96000
    duration = 10.0
    n = int(fs * duration)
    t = np.arange(n) / fs
    rng = np.random.default_rng(20260526)

    lfp_uv_rms_target = 250.0
    ap_neg_peak_uv_target = 100.0

    lfp_base = bandlimit_lfp_noise(fs, n, 1.0, 300.0, rng)
    osc = 0.60*np.sin(2*np.pi*6*t + 0.2) + 0.28*np.sin(2*np.pi*22*t + 1.1) + 0.16*np.sin(2*np.pi*78*t + 0.7)
    lfp_uv = lfp_base * (0.75 * lfp_uv_rms_target / rms(lfp_base)) + osc * 70.0
    lfp_uv = one_pole_filter(lfp_uv, 300.0, fs, mode="lowpass")
    lfp_uv = one_pole_filter(lfp_uv, 0.5, fs, mode="highpass")

    spike_times = generate_spike_train(fs, duration, firing_rate_hz=20, refractory_ms=2.0, rng=rng)
    template = spike_template(fs)
    ap_uv = add_spikes(fs, n, spike_times, template, amp_mean=1.0, amp_sigma=0.15, rng=rng) * ap_neg_peak_uv_target
    ap_noise = rng.normal(0, 4.0, n)
    ap_noise = one_pole_filter(ap_noise, 5000.0, fs, mode="lowpass")
    ap_noise = one_pole_filter(ap_noise, 300.0, fs, mode="highpass")
    ap_uv = ap_uv + ap_noise

    signals = {
        "AP_only": ap_uv,
        "LFP_only": lfp_uv,
        "AP_plus_LFP": lfp_uv + ap_uv,
    }

    metadata = {
        "fs_Hz": fs,
        "duration_s": duration,
        "wav_format": "mono 24-bit PCM WAV, peak-normalized to ±0.98 FS",
        "spike_count": int(len(spike_times)),
        "signals": {}
    }

    for name, sig_uv in signals.items():
        norm = normalize_peak(sig_uv, 0.98)
        write_wav_24bit(out_dir / f"{name}_96k_10s_peak98FS_24bit.wav", norm, fs)
        save_csv(out_dir / f"{name}_normalized_96k_10s.csv", norm, fs)
        save_csv(out_dir / f"{name}_physical_uV_96k_10s.csv", sig_uv, fs)
        metadata["signals"][name] = {
            "physical_peak_uV": float(np.max(np.abs(sig_uv))),
            "physical_rms_uV": rms(sig_uv),
            "wav_peak_FS": float(np.max(np.abs(norm))),
            "wav_rms_FS": rms(norm),
        }

    np.savetxt(out_dir / "AP_spike_times_s.csv", spike_times, delimiter=",", header="spike_time_s", comments="")
    np.savetxt(out_dir / "AP_template_normalized.csv", np.column_stack((np.arange(len(template))/fs, template)), delimiter=",", header="time_s,template_normalized_negative_peak_minus1", comments="")
    (out_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

if __name__ == "__main__":
    main()
