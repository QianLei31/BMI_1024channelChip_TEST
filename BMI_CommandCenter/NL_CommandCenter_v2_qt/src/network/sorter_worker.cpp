#include "network/sorter_worker.h"

#include <QtEndian>

#include "core/constants.h"
#include "data/data_store.h"
#include "io/session_recorder.h"

namespace ccv2 {

SorterWorker::SorterWorker(std::shared_ptr<ThreadSafeQueue<QByteArray>> inputQueue,
                           DataStore *dataStore,
                           const QVector<int> &selectedChannels,
                           SessionRecorder *recorder,
                           std::function<bool()> saveEnabledFn,
                           std::function<bool()> processEnabledFn,
                           std::atomic_bool *stopFlag,
                           QObject *parent)
    : QThread(parent),
      m_inputQueue(std::move(inputQueue)),
      m_dataStore(dataStore),
      m_selectedChannels(selectedChannels),
      m_recorder(recorder),
      m_saveEnabledFn(std::move(saveEnabledFn)),
      m_processEnabledFn(std::move(processEnabledFn)),
      m_stopFlag(stopFlag) {}

void SorterWorker::run() {
    while (!m_stopFlag->load()) {
        QByteArray chunk;
        if (!m_inputQueue->pop(chunk, 500)) {
            continue;
        }

        if (!m_processEnabledFn()) {
            continue;
        }

        if (m_saveEnabledFn()) {
            m_recorder->write(chunk);
        }

        const QByteArray fullData = m_incomplete + chunk;
        const int usable = fullData.size() - (fullData.size() % kFrameBytes);
        if (usable <= 0) {
            m_incomplete = fullData;
            continue;
        }

        const QByteArray valid = fullData.left(usable);
        m_incomplete = fullData.mid(usable);

        const int frameCount = valid.size() / kFrameBytes;
        for (int ch : m_selectedChannels) {
            QVector<qint32> values;
            values.reserve(frameCount);
            for (int f = 0; f < frameCount; ++f) {
                const char *frame = valid.constData() + f * kFrameBytes;
                const qint32 v = qFromLittleEndian<qint32>(reinterpret_cast<const uchar *>(frame + ch * kBytesPerPoint));
                values.push_back(v);
            }
            m_dataStore->appendChannelValues(ch, values);
        }
    }
}

}  // namespace ccv2
