#pragma once

#include <QByteArray>
#include <QThread>
#include <QVector>

#include <atomic>
#include <functional>
#include <memory>

#include "core/threadsafe_queue.h"

namespace ccv2 {

class DataStore;
class SessionRecorder;

class SorterWorker : public QThread {
    Q_OBJECT

public:
    SorterWorker(std::shared_ptr<ThreadSafeQueue<QByteArray>> inputQueue,
                 DataStore *dataStore,
                 const QVector<int> &selectedChannels,
                 SessionRecorder *recorder,
                 std::function<bool()> saveEnabledFn,
                 std::function<bool()> processEnabledFn,
                 std::atomic_bool *stopFlag,
                 QObject *parent = nullptr);

protected:
    void run() override;

private:
    std::shared_ptr<ThreadSafeQueue<QByteArray>> m_inputQueue;
    DataStore *m_dataStore;
    QVector<int> m_selectedChannels;
    SessionRecorder *m_recorder;
    std::function<bool()> m_saveEnabledFn;
    std::function<bool()> m_processEnabledFn;
    std::atomic_bool *m_stopFlag;
    QByteArray m_incomplete;
};

}  // namespace ccv2
