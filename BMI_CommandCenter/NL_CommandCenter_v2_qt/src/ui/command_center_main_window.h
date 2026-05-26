#pragma once

#include <QMainWindow>
#include <QStackedWidget>

#include "config/config_manager.h"
#include "core/channel_address_state.h"
#include "core/network_state.h"

class QListWidget;

namespace ccv2 {

class TopStatusBar;
class ChannelMapPanel;
class HardwareControlPanel;
class ArrayPreviewPanel;
class ChannelAnalyzerPanel;

class CommandCenterMainWindow : public QMainWindow {
    Q_OBJECT

public:
    explicit CommandCenterMainWindow(QWidget *parent = nullptr);

protected:
    void closeEvent(QCloseEvent *event) override;

private:
    void buildUi();
    void applyTheme();
    void showSettings();
    void saveUiToConfig();
    void saveNetworkToConfig(const QString &host, int port);
    void setEndpoint(const QString &host, int port, bool saveCfg, bool rememberManual);

    ConfigManager m_cfgMgr;
    NetworkState *m_networkState{nullptr};
    ChannelAddressState *m_channelState{nullptr};
    QString m_manualHost;
    int m_manualPort{10086};

    TopStatusBar *m_statusBar{nullptr};
    QListWidget *m_nav{nullptr};
    QStackedWidget *m_stack{nullptr};

    ChannelMapPanel *m_pageMap{nullptr};
    HardwareControlPanel *m_pageHw{nullptr};
    ArrayPreviewPanel *m_pagePreview{nullptr};
    ChannelAnalyzerPanel *m_pageAnalyzer{nullptr};
};

}  // namespace ccv2
