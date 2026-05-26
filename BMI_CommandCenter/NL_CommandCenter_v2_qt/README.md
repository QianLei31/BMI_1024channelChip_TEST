# NL CommandCenter V2 Qt (C++)

This folder contains the C++/Qt6 migration of Python `NL_CommandCenter_v2.py`.

## Implemented now

- Three pages:
  - SPI control page
  - Realtime 32-channel page
  - Unified monitor page (live/replay/save)
- Core read pipeline preserved:
  - TCP receive threads
  - Frame alignment by `256 * 4` bytes
  - Channel sorting and ring buffer
  - Raw stream save to `ADC_DATA.bin`
- Theme system with 5 styles, runtime switchable.

## Build prerequisites (Windows)

- Qt 6 (Core, Gui, Widgets, Network)
- CMake >= 3.20
- A C++ compiler toolchain (MSVC or MinGW)

If you use MSVC, start from `x64 Native Tools Command Prompt for VS`.

## Build

```powershell
cd e:\BMI\C_code
cmake -S . -B build -G Ninja
cmake --build build -j
```

Or with Visual Studio generator:

```powershell
cd e:\BMI\C_code
cmake -S . -B build -G "Visual Studio 17 2022" -A x64
cmake --build build --config Release
```

## Run

```powershell
.\build\NL_CommandCenter_v2_qt\NL_CommandCenter_v2_qt.exe
```

## Compatibility notes

- `config.ini` keys and defaults are aligned with Python version.
- SPI binary command encoding keeps `"spi" + hex(4 bytes)` pattern.
- Stream frame parsing keeps 256-channel, 4-byte-per-point protocol.
- Unified panel currently uses a coarse FFT for visualization; further exact parity with Python `fun_cal_sndr.py` can be added next.
