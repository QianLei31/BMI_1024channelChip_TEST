#pragma once

namespace ccv2 {

constexpr int kChannelsTotal = 256;
constexpr int kBytesPerPoint = 4;
constexpr int kFrameBytes = kChannelsTotal * kBytesPerPoint;
constexpr int kTcpBuf = 4096;
constexpr int kAdcBits = 12;
constexpr double kVref = 1.8;

}  // namespace ccv2
