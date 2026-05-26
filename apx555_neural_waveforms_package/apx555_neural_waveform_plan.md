# APx555 Neural Artificial Waveform Generation Plan

## Goal

Generate artificial neural recording waveforms for BMI chip testing using APx555/APx500 arbitrary waveform playback.

The test waveforms are divided into:

1. **AP / extracellular spike**
2. **LFP / local field potential**
3. **AP + LFP mixed wideband neural signal**

## APx555 / APx500 Playback Assumption

Use mono WAV files as arbitrary waveforms in APx500. The files in this package are 96 kHz, 10 s, mono, 24-bit PCM WAV, peak-normalized to ±0.98 FS.

Because APx generator level scaling for arbitrary waveforms depends on waveform RMS/peak definition, always verify output level by analog loopback or oscilloscope before connecting the BMI chip.

## Recommended Signal Definitions

### 1. AP-only waveform

Purpose:

- Test spike-band AFE response.
- Test spike detection threshold.
- Test ADC dynamic range for small high-frequency events.
- Test FPGA spike detection/compression.

Parameters used here:

- Sampling rate: 96000 Hz
- Duration: 10.0 s
- Nominal firing rate: 20 spikes/s
- Generated spike count: 213
- Spike template: extracellular-like biphasic/triphasic waveform
- Nominal negative peak before normalization: 100.0 µV
- Background AP-band noise: about several µVrms
- Intended analog bandwidth: 300 Hz to 5 kHz

### 2. LFP-only waveform

Purpose:

- Test low-frequency AFE response.
- Test baseline wander / low-frequency noise handling.
- Test wideband recording mode.

Parameters used here:

- Frequency range: approximately 1 Hz to 300 Hz
- Components: 1/f-like background + theta/beta/gamma components
- Nominal RMS before normalization: about 250.0 µVrms

### 3. AP + LFP waveform

Purpose:

- Test simultaneous wideband recording.
- Verify that AP events are detectable while riding on LFP background.
- Test saturation margin and digital high-pass filtering.

## Files

| File | Meaning |
|---|---|
| `AP_only_96k_10s_peak98FS_24bit.wav` | AP-only arbitrary waveform for APx playback |
| `LFP_only_96k_10s_peak98FS_24bit.wav` | LFP-only arbitrary waveform for APx playback |
| `AP_plus_LFP_96k_10s_peak98FS_24bit.wav` | Mixed neural waveform for APx playback |
| `*_normalized_96k_10s.csv` | Same waveform as WAV, normalized to digital FS |
| `*_physical_uV_96k_10s.csv` | Reference waveform in physical microvolt scale |
| `AP_spike_times_s.csv` | Ground-truth spike timestamps |
| `AP_template_normalized.csv` | Spike template used for AP generation |
| `metadata.json` | Parameters and RMS/peak statistics |
| `generate_apx555_neural_waveforms.py` | Reproducible Python generator script |

## APx555 Usage Procedure

1. Open APx500.
2. Select the analog generator output channel.
3. Choose file playback / arbitrary waveform mode.
4. Load one of the WAV files.
5. Start with a safe generator level.
6. Measure APx output with analog loopback or oscilloscope.
7. Scale generator level until the measured signal matches the desired chip-input amplitude.
8. Connect to the BMI chip through the same coupling / attenuation network used in real testing.
9. Record output data and compare against:
   - AP spike timestamps
   - AP template shape
   - LFP spectral profile
   - AP+LFP combined dynamic range

## Suggested Target Levels at Chip Input

| Test | Target level at chip input |
|---|---:|
| AP sensitivity | 30 µV, 50 µV, 100 µV, 300 µV negative peak |
| LFP dynamic range | 0.5 mVpp, 1 mVpp, 2 mVpp |
| Mixed signal | LFP 1 mVpp + AP 100 µV peak |
| Saturation margin | gradually increase LFP to front-end limit |

## Local AI / Script Modification Tasks

Ask the local AI to modify `generate_apx555_neural_waveforms.py` for:

1. Different AP firing rates: 5, 20, 50, 100 Hz.
2. Different AP amplitudes: 30, 50, 100, 300, 500 µV.
3. Different LFP profiles:
   - slow delta/theta dominant
   - beta/gamma dominant
   - stimulation artifact contaminated
4. Different file lengths: 10 s for quick bench test; 60 s for robust statistics.
5. Optional stereo WAV:
   - CH1 = AP-only
   - CH2 = LFP-only
6. Optional ground-truth JSON with every spike amplitude and timestamp.

## Important Notes

- The generated WAV files are normalized digital files, not inherently microvolt-level files.
- The physical microvolt amplitude is represented in the CSV files and metadata.
- The APx555 generator output level must be calibrated experimentally.
- For very small microvolt-level chip input, use either APx low-level output settings, external precision attenuator, or inject after an input-referred gain/attenuation fixture.
