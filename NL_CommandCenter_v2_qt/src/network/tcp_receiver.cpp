#include "network/tcp_receiver.h"

#include <QTcpSocket>

namespace ccv2 {

TcpReceiver::TcpReceiver(const QString &host, int port, const QString &cmd,
                         std::shared_ptr<ThreadSafeQueue<QByteArray>> rawQueue,
                         std::atomic_bool *stopFlag, QObject *parent)
    : QThread(parent),
      m_host(host),
      m_port(port),
      m_cmd(cmd),
      m_rawQueue(std::move(rawQueue)),
      m_stopFlag(stopFlag) {}

void TcpReceiver::run() {
    QTcpSocket socket;
    socket.connectToHost(m_host, m_port);
    if (!socket.waitForConnected(5000)) {
        m_stopFlag->store(true);
        return;
    }

    if (!m_cmd.isEmpty()) {
        socket.write(m_cmd.toUtf8());
        socket.waitForBytesWritten(1000);
    }

    while (!m_stopFlag->load()) {
        if (!socket.waitForReadyRead(1000)) {
            if (socket.state() != QAbstractSocket::ConnectedState) {
                break;
            }
            continue;
        }

        QByteArray chunk = socket.read(64 * 1024);
        if (chunk.isEmpty()) {
            if (socket.state() != QAbstractSocket::ConnectedState) {
                break;
            }
            continue;
        }

        m_rawQueue->push(chunk, true);
    }

    m_stopFlag->store(true);
    socket.disconnectFromHost();
}

}  // namespace ccv2
