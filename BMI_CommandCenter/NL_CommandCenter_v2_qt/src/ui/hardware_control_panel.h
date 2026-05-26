#pragma once

#include <QComboBox>
#include <QLabel>
#include <QLineEdit>
#include <QPlainTextEdit>
#include <QWidget>

#include <functional>

#include "config/config_manager.h"
#include "core/channel_address_state.h"
#include "core/network_state.h"

class QTcpSocket;

namespace ccv2 {

class HardwareControlPanel : public QWidget {
    Q_OBJECT

public:
    explicit HardwareControlPanel(ConfigManager *cfgMgr,
                                  NetworkState *networkState,
                                  ChannelAddressState *channelState,
                                  QWidget *parent = nullptr);

private slots:
    void saveConfig();
    void sendDirectSpi();
    void runSequence();
    void onGetChannelAddress();
    void updateNetworkHint(const QString &host, int port);

private:
    void loadAttrs();
    void buildUi();
    void log(const QString &msg, const QString &style = QString());

    QByteArray recvTcp(QTcpSocket &socket, int nbytes, int timeoutMs);
    void singleTcp(const QString &spiCmd, bool showReply = true);
    void seqRecEle16();
    void stimSend(const QString &offBit);

    ConfigManager *m_cfgMgr;
    NetworkState *m_networkState;
    ChannelAddressState *m_channelState;
    ConfigMap m_appCfg;

    QMap<QString, QLineEdit *> m_cfgEdits;

    QLineEdit *m_spiDirectEdit{nullptr};
    QComboBox *m_seqCombo{nullptr};
    QMap<QString, std::function<void()>> m_seqMap;

    QLineEdit *m_stimBlock{nullptr};
    QComboBox *m_stimAddr{nullptr};
    QLineEdit *m_stimAmp{nullptr};
    QComboBox *m_stimPolarity{nullptr};
    QComboBox *m_stimDac{nullptr};
    QComboBox *m_stimComp{nullptr};
    QComboBox *m_stimStep{nullptr};

    QLabel *m_netHintLabel{nullptr};
    QPlainTextEdit *m_addrPreview{nullptr};
    QPlainTextEdit *m_console{nullptr};
};

}  // namespace ccv2
