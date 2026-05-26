#pragma once

#include <QByteArray>
#include <QThread>

#include <atomic>
#include <memory>

#include "core/threadsafe_queue.h"

namespace ccv2 {

class SocketReceiver2 : public QThread {
    Q_OBJECT

public:
    SocketReceiver2(const QString &host, int port,
                    std::shared_ptr<ThreadSafeQueue<QByteArray>> outputQueue,
                    std::atomic_bool *stopFlag, QObject *parent = nullptr);

protected:
    void run() override;

private:
    QString m_host;
    int m_port;
    std::shared_ptr<ThreadSafeQueue<QByteArray>> m_outputQueue;
    std::atomic_bool *m_stopFlag;
};

}  // namespace ccv2
