#include "signal/sndr_calculator.h"

#include <QtMath>

#include <algorithm>
#include <complex>
#include <numeric>

namespace ccv2 {

namespace {

constexpr int kSpan = 5;
constexpr double kPi = 3.14159265358979323846;

bool isPowerOfTwo(int n) {
    return n > 0 && (n & (n - 1)) == 0;
}

double besselI0(double x) {
    double sum = 1.0;
    double y = 1.0;
    const double xx = x * x / 4.0;
    for (int k = 1; k < 30; ++k) {
        y *= xx / (static_cast<double>(k) * static_cast<double>(k));
        sum += y;
        if (y < 1e-12) {
            break;
        }
    }
    return sum;
}

QVector<double> makeWindow(int n, const QString &type) {
    QVector<double> win(n, 1.0);
    if (n <= 1) {
        return win;
    }

    if (type == QStringLiteral("hann")) {
        for (int i = 0; i < n; ++i) {
            win[i] = 0.5 - 0.5 * std::cos(2.0 * kPi * static_cast<double>(i) / static_cast<double>(n - 1));
        }
    } else if (type == QStringLiteral("blackman")) {
        for (int i = 0; i < n; ++i) {
            const double a = 2.0 * kPi * static_cast<double>(i) / static_cast<double>(n - 1);
            win[i] = 0.42 - 0.5 * std::cos(a) + 0.08 * std::cos(2.0 * a);
        }
    } else if (type == QStringLiteral("kaiser")) {
        const double beta = 20.0;
        const double den = besselI0(beta);
        for (int i = 0; i < n; ++i) {
            const double r = (2.0 * i) / static_cast<double>(n - 1) - 1.0;
            const double val = std::sqrt(std::max(0.0, 1.0 - r * r));
            win[i] = besselI0(beta * val) / den;
        }
    }
    return win;
}

QVector<std::complex<double>> fftRadix2(QVector<std::complex<double>> a) {
    const int n = a.size();
    int j = 0;
    for (int i = 1; i < n; ++i) {
        int bit = n >> 1;
        while (j & bit) {
            j ^= bit;
            bit >>= 1;
        }
        j ^= bit;
        if (i < j) {
            std::swap(a[i], a[j]);
        }
    }

    for (int len = 2; len <= n; len <<= 1) {
        const double ang = -2.0 * kPi / static_cast<double>(len);
        const std::complex<double> wlen(std::cos(ang), std::sin(ang));
        for (int i = 0; i < n; i += len) {
            std::complex<double> w(1.0, 0.0);
            for (int j2 = 0; j2 < len / 2; ++j2) {
                const std::complex<double> u = a[i + j2];
                const std::complex<double> v = a[i + j2 + len / 2] * w;
                a[i + j2] = u + v;
                a[i + j2 + len / 2] = u - v;
                w *= wlen;
            }
        }
    }
    return a;
}

QVector<std::complex<double>> dft(const QVector<std::complex<double>> &in) {
    const int n = in.size();
    QVector<std::complex<double>> out(n);
    for (int k = 0; k < n; ++k) {
        std::complex<double> sum(0.0, 0.0);
        for (int t = 0; t < n; ++t) {
            const double ang = -2.0 * kPi * static_cast<double>(k) * static_cast<double>(t) / static_cast<double>(n);
            sum += in[t] * std::complex<double>(std::cos(ang), std::sin(ang));
        }
        out[k] = sum;
    }
    return out;
}

QVector<std::complex<double>> fft(const QVector<std::complex<double>> &in) {
    if (isPowerOfTwo(in.size())) {
        return fftRadix2(in);
    }
    return dft(in);
}

double sumSlice(const QVector<double> &v, int start, int endExclusive) {
    if (v.isEmpty()) {
        return 0.0;
    }
    const int s = std::max(0, start);
    const int e = std::min(endExclusive, static_cast<int>(v.size()));
    if (e <= s) {
        return 0.0;
    }
    double sum = 0.0;
    for (int i = s; i < e; ++i) {
        sum += v[i];
    }
    return sum;
}

}  // namespace

SndrResult calSndr(const QVector<double> &data, double fs, double fb, const QString &winType) {
    SndrResult r;
    if (data.size() < 16 || fs <= 0.0 || fb <= 0.0) {
        r.error = QStringLiteral("invalid input");
        return r;
    }

    const int lenFft = data.size();
    const double resolution = fs / static_cast<double>(lenFft);
    const int lenDisplay = lenFft / 2;
    if (lenDisplay <= kSpan + 2) {
        r.error = QStringLiteral("fft size too small");
        return r;
    }

    QVector<double> win = makeWindow(lenFft, winType);
    const double mean = std::accumulate(data.begin(), data.end(), 0.0) / static_cast<double>(data.size());

    QVector<std::complex<double>> td;
    td.reserve(lenFft);
    for (int i = 0; i < lenFft; ++i) {
        td.push_back(std::complex<double>((data[i] - mean) * win[i], 0.0));
    }

    const QVector<std::complex<double>> fd = fft(td);
    QVector<double> fftData;
    fftData.reserve(lenDisplay);
    for (int i = 0; i < lenDisplay; ++i) {
        const double mag2 = std::norm(fd[i]);
        fftData.push_back(mag2);
    }

    double winNorm2 = 0.0;
    for (double w : win) {
        winNorm2 += w * w;
    }
    if (winNorm2 <= 0.0) {
        r.error = QStringLiteral("window norm error");
        return r;
    }

    for (double &v : fftData) {
        v = v / winNorm2 / fs;
    }

    QVector<double> fftFreq;
    fftFreq.reserve(lenDisplay);
    if (lenDisplay == 1) {
        fftFreq.push_back(resolution);
    } else {
        const double stop = std::round(fs / 2.0);
        const double step = (stop - resolution) / static_cast<double>(lenDisplay - 1);
        for (int i = 0; i < lenDisplay; ++i) {
            fftFreq.push_back(resolution + step * static_cast<double>(i));
        }
    }

    const int sigbandBins = 1 + static_cast<int>(std::llround(fb / resolution));
    const double sigbandPower = resolution * sumSlice(fftData, 0, sigbandBins - 1);

    int argMax = kSpan;
    for (int i = kSpan; i < lenDisplay; ++i) {
        if (fftData[i] > fftData[argMax]) {
            argMax = i;
        }
    }
    const int bin = argMax + 1;
    const double fin = (bin - 1) * resolution;

    const int nsig = 1;
    const double sigPower = resolution * sumSlice(fftData, bin - nsig, bin + nsig);
    const double dcPower = resolution * sumSlice(fftData, 0, kSpan);

    const double sndr = std::sqrt(sigPower / (sigbandPower - sigPower - dcPower));

    const double thdPower2 = resolution * sumSlice(fftData, bin * 2 - nsig, bin * 2 + nsig);
    const double thdPower3 = resolution * sumSlice(fftData, bin * 3 - nsig, bin * 3 + nsig);
    const double thdPower4 = resolution * sumSlice(fftData, bin * 4 - nsig, bin * 4 + nsig);
    const double thdPower5 = resolution * sumSlice(fftData, bin * 5 - nsig, bin * 5 + nsig);

    const double thd = std::sqrt((thdPower2 + thdPower3 + thdPower4 + thdPower5) / sigPower);

    const double sndrDb = 20.0 * std::log10(sndr);
    const double thdDb = 20.0 * std::log10(thd);
    const double enob = (sndrDb - 1.76) / 6.02;

    const double irnPower = (sigbandPower - dcPower) * 2.0;
    const double irnPowerDb = 10.0 * std::log10(irnPower);
    const double irn = std::sqrt(irnPower);

    r.sndrDb = sndrDb;
    r.enob = enob;
    r.irn = irn;
    r.fin = fin;
    r.fftData = fftData;
    r.fftFreq = fftFreq;
    r.irnPowerDb = irnPowerDb;
    r.thdDb = thdDb;
    r.ok = true;
    return r;
}

}  // namespace ccv2
