#include "signal/sndr_calculator.h"

#include <QVector>

#include <cmath>
#include <iostream>

int main() {
    constexpr double kPi = 3.14159265358979323846;
    constexpr int n = 1024;
    constexpr double fs = 20000.0;
    constexpr int toneBin = 51;
    const double finExpected = static_cast<double>(toneBin) * fs / static_cast<double>(n);

    QVector<double> data;
    data.reserve(n);
    for (int i = 0; i < n; ++i) {
        const double phase = 2.0 * kPi * static_cast<double>(toneBin) * static_cast<double>(i) / static_cast<double>(n);
        data.push_back(std::sin(phase));
    }

    const ccv2::SndrResult r = ccv2::calSndr(data, fs, fs / 2.0, QStringLiteral("hann"));
    if (!r.ok) {
        std::cerr << "calSndr failed: " << r.error.toStdString() << std::endl;
        return 1;
    }

    if (r.fftData.size() != n / 2 || r.fftFreq.size() != n / 2) {
        std::cerr << "Unexpected FFT size" << std::endl;
        return 2;
    }

    if (!std::isfinite(r.sndrDb) || !std::isfinite(r.enob) || !std::isfinite(r.fin)) {
        std::cerr << "Result contains non-finite values" << std::endl;
        return 3;
    }

    const double resolution = fs / static_cast<double>(n);
    if (std::abs(r.fin - finExpected) > resolution) {
        std::cerr << "Detected fin mismatch: " << r.fin << " vs " << finExpected << std::endl;
        return 4;
    }

    return 0;
}
