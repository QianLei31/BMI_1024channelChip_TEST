#pragma once

#include <QThread>

#include <atomic>
#include <memory>

#include "core/threadsafe_queue.h"

namespace ccv2 {

class ReplayReader : public QThread {
    Q_OBJECT

public:
    ReplayReader(const QString &adcFile,
                 std::shared_ptr<ThreadSafeQueue<QByteArray>> outputQueue,
                 std::atomic_bool *stopFlag,
                 double samplingRate,
                 double speed = 1.0,
                 QObject *parent = nullptr);

protected:
    void run() override;

private:
    QString m_adcFile;
    std::shared_ptr<ThreadSafeQueue<QByteArray>> m_outputQueue;
    std::atomic_bool *m_stopFlag;
    double m_samplingRate;
    double m_speed;
};

}  // namespace ccv2
