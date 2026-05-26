#pragma once

#include <QLabel>
#include <QLineEdit>
#include <QMap>
#include <QPushButton>
#include <QSpinBox>
#include <QTimer>
#include <QWidget>

#include <atomic>
#include <memory>

#include "config/config_manager.h"
#include "core/channel_address_state.h"
#include "core/network_state.h"
#include "core/threadsafe_queue.h"
#include "network/data_sorter.h"
#include "network/tcp_receiver.h"

namespace ccv2 {

class WaveformWidget;

class ArrayPreviewPanel : public QWidget {
    Q_OBJECT

public:
    explicit ArrayPreviewPanel(ConfigManager *cfgMgr,
                               NetworkState *networkState,
                               ChannelAddressState *channelState,
                               QWidget *parent = nullptr);
    void shutdown();
    void setWaveTheme(const QMap<QString, QString> &palette);

private slots:
    void startStream();
    void stopStream();
    void pauseStream();
    void resumeStream();
    void refresh();
    void applyChannels();
    void applyViewLength();
    void onNetworkChanged(const QString &host, int port);
    void onGetChannelAddress();

private:
    QVector<int> parseChannels() const;
    void buildUi(const QVector<int> &defaultChannels);
    bool applyChannelsInternal();
    bool applyViewLengthInternal(bool showMessage);
    int refreshIntervalMs() const;
    void updateTimeHint();

    QString m_defaultHost;
    double m_samplingRate{20000.0};
    int m_samplesPerView{1200};
    NetworkState *m_networkState;
    ChannelAddressState *m_channelState;
    std::shared_ptr<ThreadSafeQueue<QByteArray>> m_rawQueue;
    std::shared_ptr<RealtimeStreamState> m_streamState;

    std::unique_ptr<std::atomic_bool> m_stopFlag;
    TcpReceiver *m_receiver{nullptr};
    DataSorter *m_sorter{nullptr};

    bool m_paused{false};
    bool m_streaming{false};

    QLabel *m_netLabel{nullptr};
    QLineEdit *m_rtCmd{nullptr};
    QLineEdit *m_rtChEdit{nullptr};
    QSpinBox *m_rtPointsSpin{nullptr};
    QLabel *m_rtTimeHint{nullptr};
    QLabel *m_rtStatus{nullptr};
    QPushButton *m_btnGetAddrRt{nullptr};
    QPushButton *m_btnApplyAxis{nullptr};

    QPushButton *m_btnStart{nullptr};
    QPushButton *m_btnStop{nullptr};
    QPushButton *m_btnPause{nullptr};
    QPushButton *m_btnResume{nullptr};
    QPushButton *m_btnApply{nullptr};

    QVector<WaveformWidget *> m_waveWidgets;
    QTimer m_refreshTimer;
};

}  // namespace ccv2
