#include "network/data_sorter.h"

#include <QtEndian>

#include "core/constants.h"

namespace ccv2 {

DataSorter::DataSorter(std::shared_ptr<ThreadSafeQueue<QByteArray>> rawQueue,
                       std::shared_ptr<RealtimeStreamState> state,
                       std::atomic_bool *stopFlag, QObject *parent)
    : QThread(parent),
      m_rawQueue(std::move(rawQueue)),
      m_state(std::move(state)),
      m_stopFlag(stopFlag) {}

void DataSorter::run() {
    while (!m_stopFlag->load()) {
        QByteArray chunk;
        if (!m_rawQueue->pop(chunk, 200)) {
            continue;
        }

        m_leftover.append(chunk);
        const int n = (m_leftover.size() / kFrameBytes) * kFrameBytes;
        if (n <= 0) {
            continue;
        }

        const QByteArray payload = m_leftover.left(n);
        m_leftover.remove(0, n);

        QVector<int> channels;
        int maxSamples = 1200;
        {
            QMutexLocker locker(&m_state->lock);
            channels = m_state->channels;
            maxSamples = qMax(1, m_state->maxSamples);
        }
        if (channels.isEmpty()) {
            continue;
        }

        const int frameCount = payload.size() / kFrameBytes;
        QMap<int, QVector<double>> valuesByChannel;
        for (int ch : channels) {
            QVector<double> values;
            values.reserve(frameCount);
            for (int frameIndex = 0; frameIndex < frameCount; ++frameIndex) {
                const char *frame = payload.constData() + frameIndex * kFrameBytes;
                const quint32 raw = qFromLittleEndian<quint32>(
                    reinterpret_cast<const uchar *>(frame + ch * kBytesPerPoint));
                const double v = static_cast<double>(raw) / 4096.0 * 1.8;
                values.push_back(v);
            }
            valuesByChannel.insert(ch, values);
        }

        {
            QMutexLocker locker(&m_state->lock);
            for (int ch : channels) {
                auto it = valuesByChannel.constFind(ch);
                if (it == valuesByChannel.cend()) {
                    continue;
                }
                auto &q = m_state->buffers[ch];
                const QVector<double> &values = it.value();
                for (double v : values) {
                    q.enqueue(v);
                }
                while (q.size() > maxSamples) {
                    q.dequeue();
                }
            }
        }
    }
}

}  // namespace ccv2
