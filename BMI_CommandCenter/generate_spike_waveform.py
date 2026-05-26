"""
Generate a realistic BCI neural spike waveform (10 spikes in 1 second)
for APx555 arbitrary waveform generator playback.

Extracellular spike characteristics:
- Biphasic shape: negative trough (current sink) → positive overshoot (repolarization)
- Duration: ~1-2 ms per spike
- Amplitude: 50-500 µV (extracellular)
- Background: band-limited neural noise (300-3000 Hz)

APx555 AWG compatibility:
- Output format: WAV (16-bit or 24-bit PCM)
- Memory limit: 512 kpoint (this signal: 48k samples → fits)
- Sample rate: 48 kHz (safe for analog output path)
"""

import numpy as np
import wave
import os

# ── Signal Parameters ──────────────────────────────────────────────────
DURATION = 1.0              # seconds
FIRING_RATE = 10.0          # Hz (10 spikes per second)
SAMPLE_RATE = 48000         # Hz (APx555 analog output safe rate)
SPIKE_DURATION = 2.0e-3     # seconds (~2 ms, typical extracellular AP)
NOISE_AMP = 0.08            # background noise amplitude (normalized)

# Spike shape: Gaussian-mixture model for biphasic extracellular AP
# Negative trough (main deflection)
NEG_CENTER = 0.35
NEG_SIGMA = 0.06
NEG_DEPTH = -1.0

# Positive overshoot (repolarization)
POS_CENTER = 0.60
POS_SIGMA = 0.10
POS_HEIGHT = 0.4

# Small pre-potential (lead-in)
LEAD_CENTER = 0.15
LEAD_SIGMA = 0.06
LEAD_HEIGHT = 0.15

# Timing variability
JITTER_MAX_MS = 1.0         # max timing jitter per spike (ms)
AMP_VARIATION = 0.25        # ±25% amplitude variation between spikes

SEED = 42
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


def make_spike_template(n_points):
    """Generate a single biphasic spike template (extracellular AP shape)."""
    t = np.linspace(0, 1, n_points)

    lead = LEAD_HEIGHT * np.exp(-((t - LEAD_CENTER) ** 2) / (2 * LEAD_SIGMA ** 2))
    neg = NEG_DEPTH * np.exp(-((t - NEG_CENTER) ** 2) / (2 * NEG_SIGMA ** 2))
    pos = POS_HEIGHT * np.exp(-((t - POS_CENTER) ** 2) / (2 * POS_SIGMA ** 2))

    template = lead + neg + pos
    template /= np.max(np.abs(template))
    return template


def generate_bandlimited_noise(n_samples, sample_rate, low_hz=300, high_hz=3000):
    """Generate band-limited noise mimicking neural background activity."""
    white = np.random.randn(n_samples)
    # Simple FFT-based bandpass filter
    freqs = np.fft.rfftfreq(n_samples, d=1.0 / sample_rate)
    spectrum = np.fft.rfft(white)
    # Zero out frequencies outside the band
    mask = np.zeros_like(freqs, dtype=bool)
    mask[(freqs >= low_hz) & (freqs <= high_hz)] = True
    spectrum[~mask] = 0
    filtered = np.fft.irfft(spectrum, n=n_samples)
    # Normalize
    if np.std(filtered) > 0:
        filtered = filtered / np.std(filtered)
    return filtered


def generate_spike_train():
    """Generate the full 1-second spike train with noise."""
    np.random.seed(SEED)
    n_samples = int(DURATION * SAMPLE_RATE)
    spike_len = int(SPIKE_DURATION * SAMPLE_RATE)
    template = make_spike_template(spike_len)

    signal = np.zeros(n_samples)

    # Poisson-like spike timing (realistic: not perfectly regular)
    interval = DURATION / FIRING_RATE
    for i in range(int(FIRING_RATE * DURATION)):
        t_spike = i * interval + np.random.uniform(-JITTER_MAX_MS / 1000, JITTER_MAX_MS / 1000)
        center = int(t_spike * SAMPLE_RATE)
        start = center - spike_len // 2
        end = start + spike_len

        if start < 0:
            start = 0
        if end > n_samples:
            end = n_samples
        actual_len = end - start
        tmpl_start = (spike_len // 2) - (center - start)
        tmpl_end = tmpl_start + actual_len

        # Per-spike amplitude variation
        amp = 1.0 + AMP_VARIATION * (np.random.rand() - 0.5)
        signal[start:end] += amp * template[tmpl_start:tmpl_end]

    # Add band-limited neural noise
    noise = generate_bandlimited_noise(n_samples, SAMPLE_RATE)
    signal += NOISE_AMP * noise

    return signal


def save_wav_16bit(signal, filepath, sample_rate):
    """Save signal as 16-bit WAV file."""
    peak = np.max(np.abs(signal))
    if peak > 0:
        signal = signal / peak * 0.95
    int_data = (signal * 32767).astype(np.int16)

    with wave.open(filepath, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(int_data.tobytes())


def save_wav_24bit(signal, filepath, sample_rate):
    """Save signal as 24-bit WAV file."""
    peak = np.max(np.abs(signal))
    if peak > 0:
        signal = signal / peak * 0.95
    int_data = np.round(signal * (2**23 - 1)).astype(np.int32)

    with wave.open(filepath, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(3)
        wf.setframerate(sample_rate)
        raw = b''
        for val in int_data:
            val = max(-(2**23), min(2**23 - 1, val))
            raw += struct.pack('<i', val)[:3]
        wf.writeframes(raw)


def save_csv(signal, sample_rate, filepath):
    """Save as CSV for MATLAB / Python / other tools."""
    t = np.arange(len(signal)) / sample_rate
    with open(filepath, 'w') as f:
        f.write("time_s,amplitude_normalized\n")
        for ti, ai in zip(t, signal):
            f.write(f"{ti:.8f},{ai:.10e}\n")


def print_apx555_guide():
    """Print APx555 loading instructions."""
    print("\n" + "=" * 60)
    print("  APx555 Arbitrary Waveform Generator - Load Guide")
    print("=" * 60)
    print("""
  1. Open APx500 software
  2. Signal Path > Source > select 'Arbitrary Waveform'
  3. Click Browse → select 'bci_spike_10Hz_1s_16bit.wav'
  4. Waveform auto-loaded into 512 kpoint AWG memory
  5. Set output level for your BCI front-end input range
  6. Enable generator output

  Waveform specs:
    Sample rate:  48000 Hz
    Duration:     1.0 s
    Content:      10 biphasic neural spikes + background noise
    Memory used:  48000 points (fits in 512 kpoint AWG)
    Bit depth:    16-bit (or 24-bit for higher resolution)
""")


if __name__ == '__main__':
    import struct

    print("Generating BCI spike waveform for APx555...")
    print(f"  Sample rate: {SAMPLE_RATE} Hz")
    print(f"  Duration:    {DURATION} s")
    print(f"  Firing rate: {FIRING_RATE} Hz")
    print(f"  Noise band:  300-3000 Hz (neural band)")
    print()

    signal = generate_spike_train()

    # Count actual spikes in output
    n_spikes = int(FIRING_RATE * DURATION)
    print(f"  Spikes placed: {n_spikes}")

    # Save outputs
    wav16 = os.path.join(OUTPUT_DIR, "bci_spike_10Hz_1s_16bit.wav")
    wav24 = os.path.join(OUTPUT_DIR, "bci_spike_10Hz_1s_24bit.wav")
    csv_out = os.path.join(OUTPUT_DIR, "bci_spike_10Hz_1s.csv")

    save_wav_16bit(signal, wav16, SAMPLE_RATE)
    print(f"Saved: {wav16}  (16-bit, {SAMPLE_RATE} Hz, {len(signal)} samples)")

    try:
        save_wav_24bit(signal, wav24, SAMPLE_RATE)
        print(f"Saved: {wav24}  (24-bit, {SAMPLE_RATE} Hz, {len(signal)} samples)")
    except Exception as e:
        print(f"24-bit save skipped: {e}")

    save_csv(signal, SAMPLE_RATE, csv_out)
    print(f"Saved: {csv_out}  (CSV for MATLAB/Python)")

    # Print statistics
    print(f"\nSignal statistics:")
    print(f"  Peak amplitude:  {np.max(np.abs(signal)):.4f} (normalized)")
    print(f"  RMS:             {np.sqrt(np.mean(signal**2)):.4f}")
    print(f"  Peak-to-RMS:     {np.max(np.abs(signal)) / np.sqrt(np.mean(signal**2)):.1f}")

    print_apx555_guide()
