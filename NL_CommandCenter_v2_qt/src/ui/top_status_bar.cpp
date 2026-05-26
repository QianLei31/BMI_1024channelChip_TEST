#include "ui/top_status_bar.h"

#include <QHBoxLayout>
#include <QFrame>
#include <QStyle>

namespace ccv2 {

namespace {

QFrame *createSeparator() {
    auto *sep = new QFrame;
    sep->setObjectName(QStringLiteral("statusSeparator"));
    sep->setFrameShape(QFrame::VLine);
    sep->setFixedWidth(1);
    return sep;
}

}  // namespace

TopStatusBar::TopStatusBar(QWidget *parent)
    : QWidget(parent) {
    setObjectName(QStringLiteral("topStatusBar"));
    setFixedHeight(42);

    auto *layout = new QHBoxLayout(this);
    layout->setContentsMargins(12, 0, 12, 0);
    layout->setSpacing(8);

    auto *titleLabel = new QLabel(QStringLiteral("Neural Command Center V2"));
    titleLabel->setObjectName(QStringLiteral("statusTitle"));
    layout->addWidget(titleLabel);

    layout->addWidget(createSeparator());

    m_connectionBadge = new QLabel(QStringLiteral("Disconnected"));
    m_connectionBadge->setObjectName(QStringLiteral("badgeDisconnected"));
    m_connectionBadge->setProperty("class", QStringLiteral("statusBadge"));
    layout->addWidget(m_connectionBadge);

    m_endpointLabel = new QLabel(QStringLiteral("--"));
    m_endpointLabel->setObjectName(QStringLiteral("statusEndpoint"));
    layout->addWidget(m_endpointLabel);

    layout->addWidget(createSeparator());

    m_samplingRateLabel = new QLabel(QStringLiteral("Fs -- kS/s"));
    layout->addWidget(m_samplingRateLabel);

    layout->addWidget(createSeparator());

    m_activeChannelsLabel = new QLabel(QStringLiteral("CH 0"));
    layout->addWidget(m_activeChannelsLabel);

    layout->addWidget(createSeparator());

    m_packetLossBadge = new QLabel(QStringLiteral("Loss 0.00%"));
    m_packetLossBadge->setObjectName(QStringLiteral("badgeOk"));
    layout->addWidget(m_packetLossBadge);

    layout->addWidget(createSeparator());

    m_recordingBadge = new QLabel(QStringLiteral("REC OFF"));
    m_recordingBadge->setObjectName(QStringLiteral("badgeIdle"));
    layout->addWidget(m_recordingBadge);

    layout->addWidget(createSeparator());

    m_fpgaBadge = new QLabel(QStringLiteral("FPGA --"));
    m_fpgaBadge->setObjectName(QStringLiteral("badgeIdle"));
    layout->addWidget(m_fpgaBadge);

    layout->addWidget(createSeparator());

    m_stimBadge = new QLabel(QStringLiteral("STIM OFF"));
    m_stimBadge->setObjectName(QStringLiteral("badgeIdle"));
    layout->addWidget(m_stimBadge);

    layout->addStretch(1);

    m_settingsBtn = new QPushButton(QStringLiteral("Settings"));
    m_settingsBtn->setObjectName(QStringLiteral("btnSettings"));
    m_settingsBtn->setCursor(Qt::PointingHandCursor);
    connect(m_settingsBtn, &QPushButton::clicked, this, &TopStatusBar::settingsClicked);
    layout->addWidget(m_settingsBtn);
}

void TopStatusBar::setConnected(bool connected) {
    if (connected) {
        m_connectionBadge->setText(QStringLiteral("Connected"));
        m_connectionBadge->setObjectName(QStringLiteral("badgeOk"));
    } else {
        m_connectionBadge->setText(QStringLiteral("Disconnected"));
        m_connectionBadge->setObjectName(QStringLiteral("badgeDisconnected"));
    }
    m_connectionBadge->style()->unpolish(m_connectionBadge);
    m_connectionBadge->style()->polish(m_connectionBadge);
}

void TopStatusBar::setEndpoint(const QString &host, int port) {
    m_endpointLabel->setText(QStringLiteral("%1:%2").arg(host).arg(port));
}

void TopStatusBar::setSamplingRate(double fs) {
    const double ksps = fs / 1000.0;
    m_samplingRateLabel->setText(QStringLiteral("Fs %1 kS/s").arg(ksps, 0, 'f', 1));
}

void TopStatusBar::setActiveChannels(int count) {
    m_activeChannelsLabel->setText(QStringLiteral("CH %1").arg(count));
}

void TopStatusBar::setPacketLoss(double rate) {
    m_packetLossBadge->setText(QStringLiteral("Loss %1%").arg(rate, 0, 'f', 2));
    if (rate < 0.01) {
        m_packetLossBadge->setObjectName(QStringLiteral("badgeOk"));
    } else if (rate < 1.0) {
        m_packetLossBadge->setObjectName(QStringLiteral("badgeWarn"));
    } else {
        m_packetLossBadge->setObjectName(QStringLiteral("badgeError"));
    }
    m_packetLossBadge->style()->unpolish(m_packetLossBadge);
    m_packetLossBadge->style()->polish(m_packetLossBadge);
}

void TopStatusBar::setRecording(bool recording) {
    m_recordingBadge->setText(recording ? QStringLiteral("REC ON") : QStringLiteral("REC OFF"));
    m_recordingBadge->setObjectName(recording ? QStringLiteral("badgeWarn") : QStringLiteral("badgeIdle"));
    m_recordingBadge->style()->unpolish(m_recordingBadge);
    m_recordingBadge->style()->polish(m_recordingBadge);
}

void TopStatusBar::setFpgaOk(bool ok) {
    m_fpgaBadge->setText(ok ? QStringLiteral("FPGA OK") : QStringLiteral("FPGA --"));
    m_fpgaBadge->setObjectName(ok ? QStringLiteral("badgeOk") : QStringLiteral("badgeIdle"));
    m_fpgaBadge->style()->unpolish(m_fpgaBadge);
    m_fpgaBadge->style()->polish(m_fpgaBadge);
}

void TopStatusBar::setStimEnabled(bool enabled) {
    m_stimBadge->setText(enabled ? QStringLiteral("STIM ON") : QStringLiteral("STIM OFF"));
    m_stimBadge->setObjectName(enabled ? QStringLiteral("badgeWarn") : QStringLiteral("badgeIdle"));
    m_stimBadge->style()->unpolish(m_stimBadge);
    m_stimBadge->style()->polish(m_stimBadge);
}

}  // namespace ccv2
