#pragma once

#include <QByteArray>
#include <QThread>

#include <atomic>
#include <memory>

#include "core/threadsafe_queue.h"

namespace ccv2 {

class TcpReceiver : public QThread {
    Q_OBJECT

public:
    TcpReceiver(const QString &host, int port, const QString &cmd,
                std::shared_ptr<ThreadSafeQueue<QByteArray>> rawQueue,
                std::atomic_bool *stopFlag, QObject *parent = nullptr);

protected:
    void run() override;

private:
    QString m_host;
    int m_port;
    QString m_cmd;
    std::shared_ptr<ThreadSafeQueue<QByteArray>> m_rawQueue;
    std::atomic_bool *m_stopFlag;
};

}  // namespace ccv2
