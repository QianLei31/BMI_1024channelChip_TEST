#include "network/replay_reader.h"

#include <QElapsedTimer>
#include <QFile>
#include <QThread>

#include "core/constants.h"

namespace ccv2 {

ReplayReader::ReplayReader(const QString &adcFile,
                           std::shared_ptr<ThreadSafeQueue<QByteArray>> outputQueue,
                           std::atomic_bool *stopFlag,
                           double samplingRate,
                           double speed,
                           QObject *parent)
    : QThread(parent),
      m_adcFile(adcFile),
      m_outputQueue(std::move(outputQueue)),
      m_stopFlag(stopFlag),
      m_samplingRate(samplingRate),
      m_speed(qMax(0.1, speed)) {}

void ReplayReader::run() {
    QFile file(m_adcFile);
    if (!file.open(QIODevice::ReadOnly)) {
        m_stopFlag->store(true);
        return;
    }

    const double bytesPerSecond = m_samplingRate * kChannelsTotal * kBytesPerPoint;
    const int chunkBytes = qMax(1024, static_cast<int>(bytesPerSecond / 10.0));

    while (!m_stopFlag->load()) {
        QElapsedTimer timer;
        timer.start();

        QByteArray chunk = file.read(chunkBytes);
        if (chunk.isEmpty()) {
            break;
        }

        m_outputQueue->push(chunk, true);

        const double elapsed = static_cast<double>(timer.elapsed()) / 1000.0;
        const double target = (static_cast<double>(chunk.size()) / bytesPerSecond) / m_speed;
        if (target > elapsed) {
            QThread::msleep(static_cast<unsigned long>((target - elapsed) * 1000.0));
        }
    }

    file.close();
    m_stopFlag->store(true);
}

}  // namespace ccv2
