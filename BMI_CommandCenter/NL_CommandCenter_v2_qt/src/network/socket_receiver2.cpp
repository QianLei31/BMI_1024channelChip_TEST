#include "network/socket_receiver2.h"

#include <QTcpSocket>

namespace ccv2 {

SocketReceiver2::SocketReceiver2(const QString &host, int port,
                                 std::shared_ptr<ThreadSafeQueue<QByteArray>> outputQueue,
                                 std::atomic_bool *stopFlag, QObject *parent)
    : QThread(parent),
      m_host(host),
      m_port(port),
      m_outputQueue(std::move(outputQueue)),
      m_stopFlag(stopFlag) {}

void SocketReceiver2::run() {
    QTcpSocket socket;
    socket.setReadBufferSize(4 * 1024 * 1024);
    socket.connectToHost(m_host, m_port);
    if (!socket.waitForConnected(5000)) {
        m_stopFlag->store(true);
        return;
    }

    socket.write("ctread");
    socket.waitForBytesWritten(1000);

    while (!m_stopFlag->load()) {
        if (!socket.waitForReadyRead(1000)) {
            if (socket.state() != QAbstractSocket::ConnectedState) {
                break;
            }
            continue;
        }

        QByteArray chunk = socket.readAll();
        if (chunk.isEmpty()) {
            if (socket.state() != QAbstractSocket::ConnectedState) {
                break;
            }
            continue;
        }

        m_outputQueue->push(chunk, true);
    }

    socket.disconnectFromHost();
    m_stopFlag->store(true);
}

}  // namespace ccv2
