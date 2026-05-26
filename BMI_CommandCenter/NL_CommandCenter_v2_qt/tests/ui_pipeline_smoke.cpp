#include "core/constants.h"
#include "core/threadsafe_queue.h"
#include "data/data_store.h"
#include "network/data_sorter.h"
#include "network/sorter_worker.h"
#include "io/session_recorder.h"
#include "signal/sndr_calculator.h"
#include "ui/waveform_widget.h"

#include <QApplication>
#include <QByteArray>
#include <QColor>
#include <QDir>
#include <QElapsedTimer>
#include <QImage>
#include <QPainter>
#include <QQueue>
#include <QThread>
#include <QtEndian>

#include <atomic>
#include <cmath>
#include <functional>
#include <iostream>
#include <memory>

namespace {

constexpr double kPi = 3.14159265358979323846;
constexpr int kFrames = 2048;
constexpr int kToneCycles = 32;

QByteArray makeFrames()
{
    QByteArray frames(kFrames * ccv2::kFrameBytes, Qt::Uninitialized);
    for (int f = 0; f < kFrames; ++f) {
        const double phase = 2.0 * kPi * static_cast<double>(kToneCycles) *
                             static_cast<double>(f) / static_cast<double>(kFrames);
        const qint32 base = static_cast<qint32>(2048.0 + 1800.0 * std::sin(phase));
        for (int ch = 0; ch < ccv2::kChannelsTotal; ++ch) {
            const qint32 value = qBound<qint32>(0, base + (ch % 17), 4095);
            char *dst = frames.data() + f * ccv2::kFrameBytes + ch * ccv2::kBytesPerPoint;
            qToLittleEndian<qint32>(value, reinterpret_cast<uchar *>(dst));
        }
    }
    return frames;
}

bool waitFor(const std::function<bool()> &pred, int timeoutMs)
{
    QElapsedTimer timer;
    timer.start();
    while (timer.elapsed() < timeoutMs) {
        if (pred()) {
            return true;
        }
        QThread::msleep(20);
    }
    return pred();
}

bool imageHasInk(const QImage &img)
{
    const QRgb first = img.pixel(0, 0);
    int different = 0;
    for (int y = 0; y < img.height(); y += 4) {
        for (int x = 0; x < img.width(); x += 4) {
            if (img.pixel(x, y) != first) {
                ++different;
                if (different > 20) {
                    return true;
                }
            }
        }
    }
    return false;
}

bool renderWidget(ccv2::WaveformWidget &widget, const QString &path)
{
    widget.resize(640, 240);
    QImage image(widget.size(), QImage::Format_ARGB32);
    image.fill(Qt::transparent);
    QPainter painter(&image);
    widget.render(&painter);
    painter.end();
    return imageHasInk(image) && image.save(path);
}

}  // namespace

int main(int argc, char **argv)
{
    qputenv("QT_QPA_PLATFORM", QByteArray("offscreen"));
    QApplication app(argc, argv);

    const QByteArray frames = makeFrames();
    const QVector<int> channels{0, 5, 199};

    {
        auto queue = std::make_shared<ccv2::ThreadSafeQueue<QByteArray>>(16);
        auto state = std::make_shared<ccv2::RealtimeStreamState>();
        std::atomic_bool stopFlag{false};
        {
            QMutexLocker locker(&state->lock);
            state->channels = channels;
            for (int ch : channels) {
                state->buffers[ch] = QQueue<double>();
            }
        }

        ccv2::DataSorter sorter(queue, state, &stopFlag);
        sorter.start();
        queue->push(frames.left(777), true);
        queue->push(frames.mid(777, 19117), true);
        queue->push(frames.mid(777 + 19117), true);

        const bool ok = waitFor([&]() {
            QMutexLocker locker(&state->lock);
            for (int ch : channels) {
                if (state->buffers.value(ch).size() < 1200) {
                    return false;
                }
            }
            return true;
        }, 3000);
        stopFlag.store(true);
        sorter.wait(1000);
        if (!ok) {
            std::cerr << "DataSorter did not fill realtime buffers" << std::endl;
            return 1;
        }
    }

    ccv2::DataStore dataStore;
    dataStore.reset(channels, kFrames);
    {
        auto queue = std::make_shared<ccv2::ThreadSafeQueue<QByteArray>>(16);
        ccv2::SessionRecorder *recorder = nullptr;
        ccv2::SessionRecorder dummyRecorder;
        recorder = &dummyRecorder;
        std::atomic_bool stopFlag{false};
        ccv2::SorterWorker worker(queue,
                                  &dataStore,
                                  channels,
                                  recorder,
                                  []() { return false; },
                                  []() { return true; },
                                  &stopFlag);
        worker.start();
        queue->push(frames.left(513), false);
        queue->push(frames.mid(513, 32768), false);
        queue->push(frames.mid(513 + 32768), false);
        const bool ok = waitFor([&]() {
            for (int ch : channels) {
                auto *buf = dataStore.buffer(ch);
                if (!buf || buf->getLatest(kFrames).second.size() != kFrames) {
                    return false;
                }
            }
            return true;
        }, 3000);
        stopFlag.store(true);
        worker.wait(1000);
        if (!ok) {
            std::cerr << "SorterWorker did not fill DataStore buffers" << std::endl;
            return 2;
        }
    }

    QVector<double> channel0Volts;
    {
        auto *buf = dataStore.buffer(0);
        const QVector<qint32> raw = buf->getLatest(kFrames).second;
        channel0Volts.reserve(raw.size());
        for (qint32 v : raw) {
            channel0Volts.push_back(static_cast<double>(v) /
                                    static_cast<double>(1 << ccv2::kAdcBits) *
                                    ccv2::kVref);
        }
    }

    const ccv2::SndrResult sndr = ccv2::calSndr(channel0Volts, 20000.0, 10000.0, QStringLiteral("hann"));
    if (!sndr.ok || !std::isfinite(sndr.fin) || sndr.fftData.isEmpty()) {
        std::cerr << "SNDR/FFT calculation failed" << std::endl;
        return 3;
    }

    const QString outDir = QStringLiteral("E:/BMI/C_code/analysis");
    QDir().mkpath(outDir);

    ccv2::WaveformWidget single(QStringLiteral("single channel smoke"));
    single.setData(channel0Volts.mid(0, 1024));
    if (!renderWidget(single, outDir + QStringLiteral("/ccv2_ui_pipeline_single.png"))) {
        std::cerr << "Single waveform render failed" << std::endl;
        return 4;
    }

    QVector<ccv2::WaveformWidget::PlotSeries> series;
    for (int i = 0; i < channels.size(); ++i) {
        auto *buf = dataStore.buffer(channels[i]);
        const QVector<qint32> raw = buf->getLatest(1024).second;
        ccv2::WaveformWidget::PlotSeries s;
        s.color = QColor::fromHsv((i * 90) % 360, 220, 255);
        for (qint32 v : raw) {
            s.data.push_back(static_cast<double>(v) / static_cast<double>(1 << ccv2::kAdcBits) * ccv2::kVref);
        }
        series.push_back(s);
    }

    ccv2::WaveformWidget multi(QStringLiteral("multi channel smoke"));
    multi.setSeries(series);
    if (!renderWidget(multi, outDir + QStringLiteral("/ccv2_ui_pipeline_multi.png"))) {
        std::cerr << "Multi waveform render failed" << std::endl;
        return 5;
    }

    ccv2::WaveformWidget fft(QStringLiteral("fft smoke"));
    QVector<double> fftDb;
    fftDb.reserve(sndr.fftData.size());
    for (double p : sndr.fftData) {
        fftDb.push_back(10.0 * std::log10(std::max(p, 1e-18)));
    }
    fft.setYRange(-180.0, 20.0);
    fft.setData(fftDb);
    if (!renderWidget(fft, outDir + QStringLiteral("/ccv2_ui_pipeline_fft.png"))) {
        std::cerr << "FFT waveform render failed" << std::endl;
        return 6;
    }

    std::cout << "ui_pipeline_smoke ok fin=" << sndr.fin
              << " fft_bins=" << sndr.fftData.size() << std::endl;
    return 0;
}
