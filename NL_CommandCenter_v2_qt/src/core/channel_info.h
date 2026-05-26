#pragma once

#include <QString>

namespace ccv2 {

struct ChannelInfo {
    int globalChannel{0};
    int electrodeId{0};
    int blockId{0};
    int localChannel{0};
    int adcId{0};
    int stimId{0};
    int spiAddr{0};
    int dataLane{0};
    bool enabled{true};
    bool selected{false};
    bool saturated{false};
    bool packetLoss{false};
    double rms{0.0};
    double peakToPeak{0.0};
    double spikeRate{0.0};
};

struct SystemStatus {
    bool connected{false};
    QString host{QStringLiteral("127.0.0.1")};
    int port{10086};
    double samplingRate{20000.0};
    int activeChannels{0};
    double packetLossRate{0.0};
    bool recording{false};
    bool fpgaOk{false};
    bool stimEnabled{false};
    double compressionRatio{0.0};
};

enum class AcquisitionMode {
    PreviewDownsampled,
    FullRateAnalyzer,
    Playback
};

}  // namespace ccv2
