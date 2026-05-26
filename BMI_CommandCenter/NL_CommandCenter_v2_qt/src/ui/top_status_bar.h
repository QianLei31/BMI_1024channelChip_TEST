#pragma once

#include <QLabel>
#include <QPushButton>
#include <QWidget>

namespace ccv2 {

class TopStatusBar : public QWidget {
    Q_OBJECT

public:
    explicit TopStatusBar(QWidget *parent = nullptr);

    void setConnected(bool connected);
    void setEndpoint(const QString &host, int port);
    void setSamplingRate(double fs);
    void setActiveChannels(int count);
    void setPacketLoss(double rate);
    void setRecording(bool recording);
    void setFpgaOk(bool ok);
    void setStimEnabled(bool enabled);

signals:
    void settingsClicked();

private:
    QLabel *createStatusBadge(const QString &objectName);

    QLabel *m_connectionBadge{nullptr};
    QLabel *m_endpointLabel{nullptr};
    QLabel *m_samplingRateLabel{nullptr};
    QLabel *m_activeChannelsLabel{nullptr};
    QLabel *m_packetLossBadge{nullptr};
    QLabel *m_recordingBadge{nullptr};
    QLabel *m_fpgaBadge{nullptr};
    QLabel *m_stimBadge{nullptr};
    QPushButton *m_settingsBtn{nullptr};
};

}  // namespace ccv2
