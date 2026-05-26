# Neural Signal Command Center V2 UI 改造完整 Plan

## 0. 目标定义

当前软件已经具备四类核心功能：

1. **通道映射与地址解析**：从 1024 个电极/AFE 中筛选目标通道，并输出对应的 block、local channel、global channel、electrode、SPI address 等信息。
2. **硬件与 SPI 控制**：包括网络连接、配置文件、32-bit SPI 命令、全局控制命令、sequence 执行、stimulator 配置和 console output。
3. **多通道降采样预览**：选择若干通道后，以降采样方式快速查看多通道波形，用于确认系统功能、通道连通性和数据链路是否正常。
4. **单通道性能分析**：保存数据，并针对特定通道进行全速时域与频域分析，用于看噪声、频谱、干扰、带宽和 ADC/AFE 性能。

改造目标不是推翻现有软件，而是在现有 C++/Qt 框架上完成一次“产品化重构”：

> 将当前的“实验室调试工具”升级为一个“高端脑机接口控制中心”。

最终 UI 应同时满足三点：

- **好看**：深色、高对比、克制、专业，具有高端医疗仪器/神经科技 dashboard 的视觉风格。
- **有用**：保留工程调试能力，但让常用功能更直接、更清晰、更可靠。
- **可展示**：适合论文答辩、项目汇报、演示视频和实际实验使用。

---

## 1. 总体设计定位

### 1.1 视觉参考

视觉风格不建议直接参考 Intan / Open Ephys，因为这些软件功能强，但界面相对工程化。建议采用以下组合：

| 参考对象 | 主要借鉴点 | 用在本软件中的位置 |
|---|---|---|
| Neuralink / Synchron 类 neurotech 展示风格 | 黑底、极简、电极阵列、实时神经活动可视化 | 首页、通道图、多通道预览 |
| Tesla / SpaceX 控制台 | 系统链路、遥测状态、告警层级 | 顶部状态栏、系统状态、数据链路 |
| Apple Health / 医疗 dashboard | 卡片化、信息层级清晰、不过度炫酷 | 性能指标卡片、session summary |
| Intan RHX | 通道配置、滤波、spike、刺激配置 | 功能组织参考 |
| Open Ephys GUI | 模块化信号流、插件化实验流程 | 长期架构参考 |

### 1.2 功能参考

功能上继续保留当前软件的工程实用性，但重新命名和分层：

- 普通实验人员看到的是 **系统状态、通道图、波形、刺激参数、数据保存**。
- 开发调试人员可以进入 **Advanced Debug** 查看 SPI 命令、寄存器、raw console、sequence。

### 1.3 一句话定位

> 主视觉参考 neurotech dark dashboard，功能组织参考 Intan/Open Ephys，底层调试能力继续保留，但下沉到高级页面。

---

## 2. 当前 UI 的主要问题

### 2.1 信息层级不清晰

当前每页顶部都重复出现 Host、Port、Apply、Verify、Theme 等控件。这些是系统设置，不应该占据每个页面的主视觉。

建议：

- 顶部改成统一状态栏。
- Host、Port、Theme 等设置移入右上角 Settings 面板。
- 关键状态以只读状态灯显示，例如 Connected、FPGA OK、Loss 0.00%、REC OFF。

### 2.2 页面命名偏工程化

当前导航：

```text
1. 1024通道分布
2. SPI信号控制
3. 实时画图
4. Unified监控
```

问题：

- “SPI信号控制”过于底层。
- “实时画图”没有表达降采样预览的定位。
- “Unified监控”含义不明确。

建议改为：

```text
1. Channel Map / 通道映射
2. Hardware Control / 硬件控制
3. Array Preview / 阵列预览
4. Channel Analyzer / 单通道分析
5. Stimulation Designer / 刺激配置
6. Advanced Debug / 高级调试
```

如果短期只保留四页，则改为：

```text
1. 通道映射
2. 硬件控制
3. 阵列预览
4. 单通道分析
```

### 2.3 调试功能和正式功能混在一起

例如第二页同时包含 config、channel address、direct SPI command、global commands、sequence、stimulator、console output。功能是完整的，但视觉上像调试面板。

建议：

- 将常用硬件控制封装为清晰按钮。
- 将 direct SPI command、raw register、sequence runner、console output 放入 Advanced Debug 或折叠面板。

### 2.4 第三页和第四页定位没有被 UI 明确表达

实际逻辑是合理的：

- 第三页：多通道降采样预览，只看功能和趋势。
- 第四页：单通道全速分析，用于性能评估。

但目前界面没有明确提示“Preview only / Downsampled”和“Full-rate / Performance analysis”。

建议：

- 第三页命名为 Array Preview，并增加降采样提示。
- 第四页命名为 Channel Analyzer，并增加性能指标卡片。

---

## 3. 总体信息架构

推荐最终页面结构：

```text
Neural Signal Command Center V2
├── Overview / 系统总览
├── Channel Map / 通道映射
├── Hardware Control / 硬件控制
├── Array Preview / 阵列预览
├── Channel Analyzer / 单通道分析
├── Stimulation Designer / 刺激配置
├── Experiment Timeline / 实验时间轴
└── Advanced Debug / 高级调试
```

短期版本可以先做 4 页：

```text
Neural Signal Command Center V2
├── Channel Map / 通道映射
├── Hardware Control / 硬件控制
├── Array Preview / 阵列预览
└── Channel Analyzer / 单通道分析
```

中期再补充：

```text
├── Stimulation Designer / 刺激配置
├── Experiment Timeline / 实验时间轴
└── Advanced Debug / 高级调试
```

---

## 4. 全局布局设计

### 4.1 顶部状态栏

当前顶部网络配置区域建议改成全局状态栏：

```text
Neural Signal Command Center V2    Connected | 192.168.2.10:7 | Fs 20 kS/s | CH 256 | Loss 0.00% | REC OFF | FPGA OK | Theme
```

状态栏显示：

| 状态项 | 含义 |
|---|---|
| Connection | Host 是否连接 |
| Endpoint | IP:Port |
| Sampling Rate | 当前采样率 |
| Active Channels | 当前启用通道数 |
| Packet Loss | 丢包率 |
| Recording | 当前是否在记录 |
| FPGA Status | FPGA 数据链路与处理状态 |
| Stim Status | 是否有刺激输出 |
| Theme / Settings | 进入配置面板 |

### 4.2 左侧导航栏

左侧导航栏建议改为图标 + 页面名 + 简短状态：

```text
Overview             OK
Channel Map          256 selected
Hardware Control     Config loaded
Array Preview        Downsampled
Channel Analyzer     CH243
Stimulation          Disabled
Advanced Debug       Locked
```

视觉上：

- 当前选中页面使用高亮背景。
- 其他页面使用低亮度灰蓝色。
- 不要让所有按钮都使用亮蓝色。

### 4.3 主内容区

主内容区采用 card-based layout：

```text
┌──────────────────────────────────────────────────────────────┐
│ Page Header: Title + subtitle + important actions             │
├──────────────┬──────────────────────────────┬────────────────┤
│ Control Card │ Main Visualization Card       │ Inspector Card │
├──────────────┴──────────────────────────────┴────────────────┤
│ Timeline / Log / Metrics / Status                             │
└──────────────────────────────────────────────────────────────┘
```

### 4.4 右侧 Inspector

所有页面尽量有一致的右侧信息面板：

- 选中的 channel。
- 选中的 block。
- 当前状态。
- 相关 address。
- 快捷操作。

这可以让软件看起来更统一。

---

## 5. 视觉系统设计

### 5.1 颜色系统

建议使用深色主题，但加强层级。

| 用途 | 建议颜色方向 | 说明 |
|---|---|---|
| App background | near-black navy | 主背景，尽量暗 |
| Card background | dark blue-gray | 比背景略亮 |
| Card border | low-saturation blue-gray | 低亮边框 |
| Primary accent | electric blue / cyan | 关键按钮、当前页面 |
| Secondary accent | violet / soft cyan | 选中、hover、辅助信息 |
| Success | green | connected、OK、record safe |
| Warning | amber | packet loss、near saturation |
| Error | red | disconnect、overflow、unsafe stim |
| Text primary | off-white | 标题和主要数字 |
| Text secondary | blue-gray | 标签和说明 |

避免所有按钮都用亮蓝色。按钮应分级：

| 类型 | 用途 | 视觉 |
|---|---|---|
| Primary | Start、Apply、Record | 高亮填充 |
| Secondary | Save、Load、Refresh | 暗色填充或描边 |
| Danger | Reset、Stop、DAC Off | 红/橙色 |
| Ghost | Theme、Clear、Settings | 透明或弱边框 |

### 5.2 字体与数字显示

建议：

- 标题使用较粗的 sans-serif。
- 状态数字可以使用等宽字体，增强仪器感。
- 单位必须统一，例如 kS/s、Hz、V、µV、µA、ms、dB。

### 5.3 空状态设计

大面积黑框不能直接空着，应显示 placeholder。

示例：

```text
No data stream.
Click Start to begin acquisition.
```

```text
No channel selected.
Select a channel from the map.
```

```text
No FFT result.
Start recording or load a data file.
```

### 5.4 高级感的核心原则

- 少用大面积亮蓝色。
- 少用密集边框。
- 少用过多小按钮。
- 多用卡片、状态灯、数值卡片和清晰分组。
- 关键数据使用大字号。
- 工程调试内容不要放在主视觉中心。

---

## 6. 页面 1：Channel Map / 通道映射

### 6.1 页面定位

该页面用于展示 1024 AFE / electrode 与 256 ADC / 256 stimulator 的映射关系，并完成通道筛选和地址解析。

它回答的问题：

```text
我要选择哪些通道？
这些通道属于哪个 block？
对应哪个 local channel / ADC / stimulator？
SPI 地址是多少？
是否可以批量选择？
```

### 6.2 推荐布局

```text
┌──────────────────────────────────────────────────────────────────┐
│ Channel Map                                                       │
│ 1024 electrodes | 64 blocks | 256 ADCs | 256 stimulators          │
├───────────────┬───────────────────────────────────┬──────────────┤
│ Selection     │ 64-block / 1024-channel map        │ Inspector    │
│ Block range   │                                   │ Global CH    │
│ Local CH      │     Block / electrode grid         │ Block        │
│ Batch select  │                                   │ Local CH     │
│ Clear         │                                   │ ADC          │
│ Apply         │                                   │ Stimulator   │
│               │                                   │ SPI Addr     │
├───────────────┴───────────────────────────────────┴──────────────┤
│ Selected channel table / address output / copy result             │
└──────────────────────────────────────────────────────────────────┘
```

### 6.3 通道图建议

建议从当前静态大图升级为两级可视化：

#### Level 1：64-block map

8×8 block grid，每个 block 显示：

- Block ID。
- 已选通道数。
- ADC 状态。
- Stim 状态。
- Packet error 或 disabled 状态。

#### Level 2：block 内部 16 AFE 展开

点击某个 block 后，在右侧显示该 block 的内部结构：

```text
Block 12
AFE 0  AFE 1  AFE 2  AFE 3
AFE 4  AFE 5  AFE 6  AFE 7
AFE 8  AFE 9  AFE10  AFE11
AFE12  AFE13  AFE14  AFE15

ADC0 handles local 00
ADC1 handles local 01
ADC2 handles local 10
ADC3 handles local 11
```

### 6.4 右侧 Inspector 卡片

选中通道后显示：

```text
Selected Channel
Global CH      243
Block          15
Local CH       03
Electrode      E243
ADC            ADC3
Stimulator     STIM3
SPI Addr       0x2B
Data Lane      Lane 7
Status         Enabled
```

### 6.5 批量选择功能

保留当前快速选择功能，但优化成更清晰的控件：

```text
Block Range     0-63
Local Channel   00  01  10  11
Global Channel  0-255 / comma-separated list
Buttons         Select / Unselect / Clear / Apply
```

### 6.6 输出区域

底部输出不要只显示普通文本，建议做成 table：

| Global CH | Block | Local CH | Electrode | ADC | Stim | SPI Addr |
|---|---:|---:|---:|---:|---:|---:|
| 0 | 0 | 00 | E000 | ADC0 | STIM0 | 0x00 |
| 8 | 2 | 00 | E008 | ADC0 | STIM0 | 0x02 |

并提供：

- Copy CSV。
- Copy SPI sequence。
- Export JSON。

---

## 7. 页面 2：Hardware Control / 硬件控制

### 7.1 页面定位

该页面用于完成硬件连接、配置加载、初始化、全局控制命令和常用 sequence 执行。

它不是 raw SPI console。raw SPI 应该下沉到 Advanced Debug。

### 7.2 推荐布局

```text
┌──────────────────────────────────────────────────────────────────┐
│ Hardware Control                                                  │
│ Endpoint 192.168.2.10:7 | Config loaded | Link OK                 │
├─────────────────────────┬────────────────────────────────────────┤
│ Connection              │ Console / System Log                    │
│ Host / Port             │                                        │
│ Connect / Verify        │                                        │
│                         │                                        │
│ Configuration           │                                        │
│ Load / Save / Apply     │                                        │
│                         │                                        │
│ Global Commands         │                                        │
│ Reset / DAC On / DAC Off│                                        │
│                         │                                        │
│ Sequence                │                                        │
│ Select / Run            │                                        │
└─────────────────────────┴────────────────────────────────────────┘
```

### 7.3 Basic Control 区域

保留并产品化以下按钮：

- Load Configuration。
- Save Configuration。
- Apply Configuration。
- Verify Link。
- Analog Reset。
- Analog Remove Reset。
- Global DAC On。
- Global DAC Off。
- Run Initialization Sequence。

### 7.4 Advanced SPI 折叠区

不要默认展开 direct 32-bit SPI command。改为折叠：

```text
Advanced SPI Console  [Locked / Expand]
├── Direct 32-bit command
├── Register address
├── Register value
├── Send
├── Readback
└── Raw console output
```

建议加一个确认机制：

```text
Enable Advanced SPI Mode
```

避免误操作。

### 7.5 Console Output 优化

Console 建议支持：

- 时间戳。
- 日志等级：INFO / WARN / ERROR / TX / RX。
- 搜索。
- Clear。
- Export log。

示例：

```text
[12:01:03.120] INFO  Link verified: 192.168.2.10:7
[12:01:03.220] TX    SPI 0x0000FFFF
[12:01:03.225] RX    ACK
[12:01:04.010] WARN  Packet loss counter increased: lane 3
```

---

## 8. 页面 3：Array Preview / 阵列预览

### 8.1 页面定位

该页面是多通道降采样预览页面。它用于快速看系统是否工作、哪些通道有信号、数据链路是否稳定，而不是用于精确性能评估。

核心定位：

> 低速、多通道、看趋势、看功能、看状态。

### 8.2 页面顶部必须明确提示

建议加入提示条：

```text
Preview Mode | Downsampled Display | Not for Performance Measurement
```

中文：

```text
当前为降采样预览模式，仅用于多通道状态观察；单通道性能请进入 Channel Analyzer。
```

### 8.3 推荐布局

```text
┌──────────────────────────────────────────────────────────────────┐
│ Array Preview                                                     │
│ Downsampled | Display refresh 10 Hz | Selected 32 channels        │
├───────────────┬───────────────────────────────────┬──────────────┤
│ Channel Set   │ Multi-channel waveform preview     │ Status Map   │
│ CH list       │                                   │ RMS          │
│ Block select  │ CH0   ─────────────               │ Saturation   │
│ Apply         │ CH8   ─────────────               │ Packet loss  │
│ View Mode     │ CH16  ─────────────               │ Active count │
│ Stack / Tile  │ CH24  ─────────────               │              │
├───────────────┴───────────────────────────────────┴──────────────┤
│ Event preview / dropped packet / warning timeline                 │
└──────────────────────────────────────────────────────────────────┘
```

### 8.4 显示模式

建议提供 3 种模式：

#### 8.4.1 Stack View：默认推荐

多通道纵向堆叠，适合快速判断信号形态：

```text
CH0    ─────╮╭──────
CH8    ─────────────
CH16   ───╮╭────────
CH24   ─────────╮╭──
```

优点：

- 比 32 个小图更节省空间。
- 更像专业神经信号软件。
- 波形之间容易比较。

#### 8.4.2 Tile View：保留当前小图模式

当前 4×8 或 8×4 小图可以保留，但建议：

- 默认显示 8 或 16 个通道。
- 32 个通道作为可选项。
- 空图不要只显示坐标轴，应有 placeholder 或隐藏。

#### 8.4.3 Activity Map：强烈建议加入

显示 256 通道或 1024 electrode 的状态热图：

- RMS。
- Peak-to-peak。
- Spike count。
- Saturation。
- Packet loss。
- Disabled。

### 8.5 控件设计

左侧控制区建议包含：

```text
Channel Preset
- All ADC0
- All ADC1
- Block 0-7
- Custom list

Display
- Stack View
- Tile View
- Activity Map

Downsample
- Auto
- 10×
- 100×

Refresh Rate
- 5 Hz
- 10 Hz
- 20 Hz
```

### 8.6 不建议在此页加入的内容

不建议加入：

- 精确 FFT。
- SNDR / ENOB。
- 复杂保存功能。
- 过多 SPI 控件。

这些应留给 Channel Analyzer 或 Hardware Control。

---

## 9. 页面 4：Channel Analyzer / 单通道分析

### 9.1 页面定位

该页面是单通道高精度性能分析页面，用于全速采集、保存数据、查看时域、频域和性能指标。

核心定位：

> 全速、单通道、看性能、保存数据、回放分析。

### 9.2 推荐布局

```text
┌──────────────────────────────────────────────────────────────────┐
│ Channel Analyzer                                                  │
│ CH243 | Block 15 | ADC3 | Full-rate | Fs 20 kS/s                 │
├───────────────┬──────────────────────────────────────────────────┤
│ Control       │ Time-domain waveform                             │
│ Channel       │                                                  │
│ Fs            ├──────────────────────────────────────────────────┤
│ FFT points    │ Frequency spectrum / PSD                         │
│ Window        │                                                  │
│ Save path     ├──────────────────────────────────────────────────┤
│ Record        │ Metrics cards                                    │
│ Playback      │ RMS | P2P | Noise density | SNR | THD | SFDR     │
└───────────────┴──────────────────────────────────────────────────┘
```

### 9.3 控制区

建议包含：

```text
Channel
- Global channel
- Block / local channel readback
- ADC ID

Acquisition
- Sampling rate
- Number of points
- Record duration
- Start / Stop / Pause

FFT / PSD
- FFT points
- Window: Hann / Blackman / Rectangular
- Frequency range
- dBFS / dBV / μV/√Hz

Storage
- Save directory
- File prefix
- Save raw binary
- Save CSV
- Save metadata JSON

Playback
- Load file
- Analyze file
```

### 9.4 性能指标卡片

建议在图下方或右侧加入指标卡片：

```text
RMS Noise          4.8 μVrms
Peak-to-Peak       32.5 μV
Noise Density      80 nV/√Hz
50/60 Hz Power     -72 dB
Saturation Ratio   0.00%
Packet Loss        0.000%
```

如果用于 ADC 正弦测试，可加入：

```text
Main Tone          1.02 kHz
SNDR               72.4 dB
SFDR               84.1 dB
THD                -78.5 dB
ENOB               11.7 bit
Noise Floor        -112 dBFS
```

### 9.5 图形显示建议

#### Time-domain waveform

- 支持 raw / filtered 切换。
- 支持 voltage / code 切换。
- 支持自动量程。
- 显示 selected time window。

#### Frequency spectrum / PSD

- 支持 FFT 和 PSD 两种模式。
- 支持 dBFS、dBV、µV²/Hz、µV/√Hz。
- 支持标出主频、谐波、50/60 Hz。

#### 数据质量提示

当数据不足或设置不合理时，给出明确提示：

```text
FFT points are larger than current buffer length.
```

```text
Input is saturated. Frequency metrics may be invalid.
```

```text
Packet loss detected. Save file is marked as incomplete.
```

---

## 10. 页面 5：Stimulation Designer / 刺激配置

### 10.1 页面定位

当前 Stimulator 功能埋在 SPI 控制页下方，不能突出系统价值。建议独立做成一页。

它回答的问题：

```text
刺激哪个通道？
刺激电流多大？
脉宽多少？
频率多少？
是否双相？
触发方式是什么？
是否满足安全限制？
```

### 10.2 推荐布局

```text
┌──────────────────────────────────────────────────────────────────┐
│ Stimulation Designer                                              │
│ 256 programmable stimulators | Manual / FPGA trigger / External   │
├───────────────┬───────────────────────────────────┬──────────────┤
│ Channel Select│ Stimulation waveform editor        │ Safety       │
│ CH / block    │                                   │ Charge/phase │
│ Stim ID       │      cathodic / anodic preview     │ Balance      │
│ Mode          │                                   │ Limit        │
│ Amplitude     │                                   │ Compliance   │
│ Pulse width   │                                   │ Status       │
│ Frequency     │                                   │              │
└───────────────┴───────────────────────────────────┴──────────────┘
```

### 10.3 波形编辑器

不要只用表格输入，应有波形预览：

```text
        cathodic            anodic
          ┌────┐             ┌────┐
──────────┘    └─────────────┘    └────────
          PW       Gap        PW
```

控件：

```text
Channel:        CH243
Mode:           Biphasic / Monophasic
Amplitude:      0-100 µA / High range up to 2 mA
Pulse width:    50-500 µs
Interphase gap: 20 µs
Frequency:      1-200 Hz
Train duration: 1 s
Trigger source: Manual / FPGA spike / External TTL / Software
```

### 10.4 安全检查

右侧 safety card：

```text
Charge per phase      8 nC
Charge balance        OK
Current range         Normal
Compliance            OK
Interlock             Enabled
Stim output           Disabled
```

危险操作如 Enable Stim / Start Train 必须使用明显的确认状态。

---

## 11. 页面 6：Experiment Timeline / 实验时间轴

### 11.1 页面定位

该页面用于展示 FPGA spike detection、压缩、无线传输、闭环触发和刺激响应，是系统级成果展示页。

它回答的问题：

```text
什么时候检测到 spike？
什么时候触发刺激？
触发延迟是多少？
压缩率是多少？
无线链路是否稳定？
刺激后是否有响应？
```

### 11.2 推荐布局

```text
┌──────────────────────────────────────────────────────────────────┐
│ Experiment Timeline                                               │
│ Closed-loop flow | Spike detection | Compression | Stimulation    │
├──────────────────────────────────────────────────────────────────┤
│ Chip → FPGA Detector → Compressor → Wireless → Host → Stim Trigger│
├──────────────────────────────────────────────────────────────────┤
│ Event Timeline                                                    │
│ t0          Spike detected on CH037                               │
│ t0 + 0.8 ms Trigger generated                                     │
│ t0 + 1.2 ms Stimulator CH112 enabled                              │
│ t0 + 3.5 ms Response detected                                     │
├──────────────────────────────────────────────────────────────────┤
│ Session Summary                                                   │
│ Events | Compression ratio | Packet loss | Avg latency | Stim count│
└──────────────────────────────────────────────────────────────────┘
```

### 11.3 Session Summary

记录结束后自动生成摘要：

```text
Duration:             30 min
Active channels:      241 / 256
Average noise:        5.1 µVrms
Detected events:      1.2 M
Compression ratio:    18.6×
Packet loss:          0.003%
Stim pulses:          320
Average latency:      1.2 ms
```

---

## 12. 页面 7：Advanced Debug / 高级调试

### 12.1 页面定位

保留全部底层工程能力，但不要占据主流程页面。

功能：

- Direct 32-bit SPI command。
- Register table。
- Sequence editor。
- Raw TX/RX log。
- Packet monitor。
- Error counter。
- Debug export。

### 12.2 推荐布局

```text
┌──────────────────────────────────────────────────────────────────┐
│ Advanced Debug                                                    │
│ Warning: low-level commands may change hardware state             │
├──────────────────────────┬───────────────────────────────────────┤
│ SPI Console              │ Register Table                         │
│ Command input            │ Addr | Name | Value | Description      │
│ Send / Readback          │                                       │
├──────────────────────────┴───────────────────────────────────────┤
│ Raw console / packet monitor                                      │
└──────────────────────────────────────────────────────────────────┘
```

建议进入该页面时显示提示：

```text
Advanced Debug Mode is intended for hardware developers.
Incorrect commands may reset or misconfigure the chip.
```

---

## 13. 数据与通道模型

为了支持 UI 统一，建议在程序内部建立统一的 channel model。

### 13.1 ChannelInfo

每个通道维护：

```cpp
struct ChannelInfo {
    int globalChannel;      // 0-255 or 0-1023 depending on view
    int electrodeId;        // 0-1023
    int blockId;            // 0-63
    int localChannel;       // 0-15 for AFE, or 0-3 for ADC selection
    int adcId;              // 0-255 or local 0-3
    int stimId;             // 0-255 or local 0-3
    int spiAddr;
    int dataLane;
    bool enabled;
    bool selected;
    bool saturated;
    bool packetLoss;
    double rms;
    double peakToPeak;
    double spikeRate;
};
```

### 13.2 SystemStatus

全局状态维护：

```cpp
struct SystemStatus {
    bool connected;
    QString host;
    int port;
    double samplingRate;
    int activeChannels;
    double packetLossRate;
    bool recording;
    bool fpgaOk;
    bool stimEnabled;
    double compressionRatio;
};
```

### 13.3 AcquisitionMode

明确区分第三页和第四页：

```cpp
enum class AcquisitionMode {
    PreviewDownsampled,   // 第三页，多通道低速预览
    FullRateAnalyzer,     // 第四页，单通道全速分析
    Playback              // 离线文件回放
};
```

---

## 14. 数据流与性能要求

### 14.1 第三页 Array Preview

目标：流畅、低负载、多通道。

建议：

- 后端全速接收数据。
- UI 只取降采样后的 display buffer。
- UI 刷新率 5-20 Hz。
- 每通道显示点数控制在 500-2000 点。
- 不做高成本 FFT。

### 14.2 第四页 Channel Analyzer

目标：准确、全速、可保存、可分析。

建议：

- 单通道全速 buffer。
- 支持固定点数采集，例如 4096 / 8192 / 16384 / 65536。
- 支持保存 raw binary + metadata JSON。
- FFT 与 PSD 可在采集后计算，避免阻塞 UI。
- 支持实时分析和离线回放。

### 14.3 绘图性能建议

如果继续使用 Qt/C++：

- 少量高性能曲线可以用 QCustomPlot / Qwt / Qt Charts。
- 多通道实时波形建议使用 OpenGL 加速或自定义绘制。
- 不建议用过多独立 QWidget plot，32 个以上小图会明显增加 UI 负载。
- Stack View 比大量 Tile View 更容易优化。

---

## 15. 文件保存格式建议

建议保存时至少包含两个文件：

```text
session_2026_05_14_120103_ch243.bin
session_2026_05_14_120103_ch243.json
```

### 15.1 raw binary

保存原始 ADC code 或电压转换后的数据。

### 15.2 metadata JSON

示例：

```json
{
  "software": "Neural Signal Command Center V2",
  "channel": 243,
  "block": 15,
  "adc": 3,
  "sampling_rate": 20000,
  "fft_points": 16384,
  "unit": "ADC code",
  "start_time": "2026-05-14T12:01:03",
  "duration_s": 10,
  "packet_loss_rate": 0.0,
  "config_file": "config.ini",
  "notes": "full-rate channel analyzer recording"
}
```

这样后续写论文、复现实验、离线分析都会方便很多。

---

## 16. 当前四页的具体改造路线

### 16.1 当前第 1 页：1024通道分布

改造为：

```text
Channel Map / 通道映射
```

保留：

- 通道分布图。
- block/local/global/channel 选择。
- 地址输出。

新增：

- 64-block overview。
- Selected Channel Inspector。
- 地址输出表格化。
- Copy CSV / Export JSON。
- 颜色状态：selected / enabled / disabled / error / stim active。

### 16.2 当前第 2 页：SPI信号控制

改造为：

```text
Hardware Control / 硬件控制
```

保留：

- config.ini 读取与保存。
- channel address 获取。
- global commands。
- sequence run。
- stimulator 初步配置。
- console output。

调整：

- direct 32-bit SPI command 放入 Advanced SPI 折叠区。
- console output 增加时间戳、日志等级、导出。
- 常用控制做成 Basic Control。

### 16.3 当前第 3 页：实时画图

改造为：

```text
Array Preview / 阵列预览
```

保留：

- 多通道选择。
- Start / Stop / Pause / Resume。
- 降采样显示。

新增：

- Downsampled preview 提示条。
- Stack View 默认模式。
- Tile View 可选。
- Activity Map 可选。
- 通道健康指标：RMS preview、saturation、packet loss。

### 16.4 当前第 4 页：Unified监控

改造为：

```text
Channel Analyzer / 单通道分析
```

保留：

- 保存数据。
- 单通道时域图。
- 单通道频域图。
- FFT 参数。

新增：

- Full-rate mode 提示。
- 性能指标卡片。
- Live / Playback 模式。
- raw binary + metadata JSON 保存。
- 频谱单位切换。
- 数据质量 warning。

---

## 17. 分阶段实施计划

### Phase 0：整理现有代码结构

目标：不改功能，先建立清晰结构。

任务：

- 将页面类重命名为 ChannelMapPage、HardwareControlPage、ArrayPreviewPage、ChannelAnalyzerPage。
- 抽离通用 TopStatusBar。
- 抽离 LeftNavigation。
- 抽离 ConsoleWidget。
- 抽离 ChannelInfo / SystemStatus 数据结构。

验收标准：

- 现有功能不损坏。
- 四个页面名称和导航已更新。
- 顶部状态栏统一。

### Phase 1：视觉系统统一

目标：让软件整体观感从工程工具变成 dark dashboard。

任务：

- 重做 QSS / theme。
- 建立统一颜色变量。
- 统一 button、card、input、table、plot 的样式。
- 取消所有按钮同一亮蓝色的设计。
- 增加 empty state。

验收标准：

- 所有页面视觉风格一致。
- 主要/次要/危险按钮可区分。
- 空图、空 console、空选择区域有 placeholder。

### Phase 2：Channel Map 升级

目标：让通道选择和地址解析更清楚。

任务：

- 增加 Selected Channel Inspector。
- 地址输出表格化。
- 批量选择功能整理。
- 加入 selected/enabled/error/stim active 状态颜色。
- 支持复制和导出。

验收标准：

- 点击任意通道可显示完整 mapping。
- 批量选择结果可复制。
- 页面不再只是静态通道图。

### Phase 3：Array Preview 升级

目标：第三页明确成为多通道降采样预览。

任务：

- 页面标题改为 Array Preview。
- 加入 downsampled preview 提示。
- 增加 Stack View。
- Tile View 保留但优化默认通道数。
- 增加 activity map 或 RMS preview map。

验收标准：

- 用户一眼能看出该页不是性能分析页。
- 多通道预览更清晰。
- UI 刷新不卡顿。

### Phase 4：Channel Analyzer 升级

目标：第四页成为真正的单通道性能分析工具。

任务：

- 页面标题改为 Channel Analyzer。
- 增加 channel info header。
- 增加 full-rate mode 提示。
- 增加 RMS、P2P、PSD、packet loss 等指标卡片。
- 增加 Live / Playback 模式。
- 保存 metadata JSON。

验收标准：

- 采集一个通道后能直接看到时域、频域和关键指标。
- 保存数据可复现分析条件。
- FFT/PSD 不阻塞 UI。

### Phase 5：Stimulation Designer 独立页面

目标：突出 256 通道刺激器能力。

任务：

- 新建 Stimulation Designer 页面。
- 增加 channel/stim selection。
- 增加 biphasic waveform preview。
- 增加 amplitude、pulse width、gap、frequency、train duration。
- 增加 safety card。
- 底层仍调用现有 SPI/stimulator 配置逻辑。

验收标准：

- 不需要看 SPI 命令即可配置刺激参数。
- UI 能预览刺激波形。
- 有基本安全提示。

### Phase 6：Experiment Timeline 与演示页

目标：服务论文、答辩和系统展示。

任务：

- 增加 closed-loop flow diagram。
- 增加 event timeline。
- 增加 compression ratio / latency / event count。
- 增加 session summary。

验收标准：

- 可以展示 spike detection → compression → wireless → host → stimulation 的系统链路。
- 实验结束可生成 summary。

---

## 18. 给 Codex / Spec 模式的任务拆分建议

### Task 1：Refactor page names and navigation

目标：只改页面名称和导航，不改底层逻辑。

输入：当前 Qt/C++ 工程。

输出：

- Channel Map。
- Hardware Control。
- Array Preview。
- Channel Analyzer。

验收：四页功能与原来一致，导航名称更新。

### Task 2：Create global status bar component

目标：替代每页重复的 Host/Port 区域。

输出：

- TopStatusBar widget。
- 显示 connection、endpoint、sampling rate、active channels、packet loss、recording、FPGA status。
- Settings 按钮打开 host/port/theme 配置。

### Task 3：Create dark dashboard QSS theme

目标：统一界面视觉。

输出：

- Dark theme QSS。
- Button styles: primary / secondary / danger / ghost。
- Card style。
- Input style。
- Table style。
- Plot background style。

### Task 4：Upgrade Channel Map inspector

目标：增加右侧选中通道信息卡片。

输出：

- SelectedChannelCard。
- Channel address table。
- Copy/export。

### Task 5：Implement Array Preview stack view

目标：把第三页默认显示从大量 tile 小图改为 stack view。

输出：

- StackWaveformView。
- TileView 作为可切换模式保留。
- Downsampled preview warning banner。

### Task 6：Upgrade Channel Analyzer metrics

目标：第四页增加单通道性能指标。

输出：

- Metrics cards。
- FFT/PSD control。
- Data quality warning。
- Metadata JSON save。

### Task 7：Add Stimulation Designer page

目标：将刺激器从 SPI 页面中独立出来。

输出：

- Stimulation parameter panel。
- Waveform preview。
- Safety card。
- Apply to hardware。

---

## 19. 最终推荐界面草图

### 19.1 总体框架

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Neural Signal Command Center V2  Connected | Fs 20 kS/s | Loss 0.00% | REC  │
├───────────────┬──────────────────────────────────────────────────────────────┤
│ Channel Map   │ Page Title                                                   │
│ Hardware Ctrl │ Subtitle / Mode / Important Status                           │
│ Array Preview │                                                              │
│ Analyzer      │ Main content                                                  │
│ Stimulation   │                                                              │
│ Debug         │                                                              │
└───────────────┴──────────────────────────────────────────────────────────────┘
```

### 19.2 Array Preview

```text
┌──────────────────────────────────────────────────────────────────────┐
│ Array Preview | Downsampled Display | Selected 32 channels            │
├──────────────┬────────────────────────────────────┬──────────────────┤
│ Channel Set  │ Stack Waveform View                 │ Activity Map     │
│ Presets      │ CH0   ─────────────                 │ RMS / Spike / Err│
│ Block range  │ CH8   ─────────────                 │                  │
│ View mode    │ CH16  ─────────────                 │ 16×16 grid       │
│ Apply        │ CH24  ─────────────                 │                  │
└──────────────┴────────────────────────────────────┴──────────────────┘
```

### 19.3 Channel Analyzer

```text
┌──────────────────────────────────────────────────────────────────────┐
│ Channel Analyzer | CH243 | Full-rate | Fs 20 kS/s                    │
├──────────────┬───────────────────────────────────────────────────────┤
│ Control      │ Time-domain waveform                                  │
│ Channel      ├───────────────────────────────────────────────────────┤
│ FFT points   │ Frequency spectrum / PSD                              │
│ Window       ├───────────────────────────────────────────────────────┤
│ Save path    │ RMS | P2P | Noise density | SNR | THD | SFDR | Loss    │
└──────────────┴───────────────────────────────────────────────────────┘
```

---

## 20. 最关键的设计结论

1. **不要把软件继续做成 SPI 调试工具。**  SPI 很重要，但应下沉到 Hardware Control / Advanced Debug。

2. **第三页和第四页不要合并。**  第三页是多通道降采样预览，第四页是单通道全速性能分析，两者定位不同。

3. **第三页必须明确写 Preview / Downsampled。**  否则别人会误以为该页可以用于性能测试。

4. **第四页要增加性能指标卡片。**  单有时域和频域图不够，要直接给出 RMS、P2P、PSD、packet loss，必要时给 SNDR、SFDR、THD、ENOB。

5. **刺激器应该独立成页。**  256 可编程刺激器是系统卖点，不应该隐藏在 SPI 面板里。

6. **高端感来自清晰的信息层级，而不是更多炫光。**  深色主题、卡片、状态栏、activity map、inspector、timeline，会比堆按钮和堆小图更高级。

7. **不建议推翻重写。**  最合理路线是在当前 Qt/C++ 软件上做分阶段重构：先统一布局和视觉，再逐步升级每一页。
