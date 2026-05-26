#pragma once

#include <QObject>
#include <QString>

namespace ccv2 {

class NetworkState : public QObject {
    Q_OBJECT

public:
    explicit NetworkState(const QString &host, int port, QObject *parent = nullptr)
        : QObject(parent), m_host(host.trimmed().isEmpty() ? QStringLiteral("127.0.0.1") : host.trimmed()), m_port(port) {}

    QString host() const { return m_host; }
    int port() const { return m_port; }

    void setEndpoint(const QString &host, int port) {
        const QString normalizedHost = host.trimmed().isEmpty() ? QStringLiteral("127.0.0.1") : host.trimmed();
        const int normalizedPort = port;
        if (normalizedHost == m_host && normalizedPort == m_port) {
            return;
        }
        m_host = normalizedHost;
        m_port = normalizedPort;
        emit endpointChanged(m_host, m_port);
    }

signals:
    void endpointChanged(const QString &host, int port);

private:
    QString m_host;
    int m_port{10086};
};

}  // namespace ccv2
