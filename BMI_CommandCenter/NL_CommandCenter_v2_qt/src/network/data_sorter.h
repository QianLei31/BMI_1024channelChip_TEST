#pragma once

#include <QByteArray>
#include <QMap>
#include <QMutex>
#include <QQueue>
#include <QThread>
#include <QVector>

#include <atomic>
#include <memory>

#include "core/threadsafe_queue.h"

namespace ccv2 {

struct RealtimeStreamState {
    QMutex lock;
    QVector<int> channels;
    QMap<int, QQueue<double>> buffers;
    int maxSamples{1200};
};

class DataSorter : public QThread {
    Q_OBJECT

public:
    DataSorter(std::shared_ptr<ThreadSafeQueue<QByteArray>> rawQueue,
               std::shared_ptr<RealtimeStreamState> state,
               std::atomic_bool *stopFlag, QObject *parent = nullptr);

protected:
    void run() override;

private:
    std::shared_ptr<ThreadSafeQueue<QByteArray>> m_rawQueue;
    std::shared_ptr<RealtimeStreamState> m_state;
    std::atomic_bool *m_stopFlag;
    QByteArray m_leftover;
};

}  // namespace ccv2
