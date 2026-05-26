#pragma once

#include <QCheckBox>
#include <QComboBox>
#include <QDoubleSpinBox>
#include <QElapsedTimer>
#include <QLabel>
#include <QLineEdit>
#include <QPlainTextEdit>
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
#include "data/data_store.h"
#include "io/session_recorder.h"
#include "network/replay_reader.h"
#include "network/socket_receiver2.h"
#include "network/sorter_worker.h"

namespace ccv2 {

class WaveformWidget;

struct RuntimeConfig {
    QString host{QStringLiteral("localhost")};
    int port{10086};
    double samplingRate{20000.0};
    int fftPoints{16384};
    QString saveDir{QStringLiteral("d:/ADC_data")};
};

class ChannelAnalyzerPanel : public QWidget {
    Q_OBJECT

public:
    explicit ChannelAnalyzerPanel(ConfigManager *cfgMgr,
                                  NetworkState *networkState,
                                  ChannelAddressState *channelState,
                                  QWidget *parent = nullptr);
    void shutdown();
    void setPlotTheme(const QString &plotBg, const QString &plotAxis);

private slots:
    void rebuildSessionName();
    void loadFolder();
    void startLive();
    void startReplay();
    void pauseView();
    void resumeView();
    void stopAll();
    void updatePlots();
    void onNetworkChanged(const QString &host, int port);
    void onGetChannelAddress();
    void checkNetworkConnectivity();

private:
    QPair<QVector<QVector<int>>, QVector<int>> parseChannelGroups(const QString &text) const;
    QPair<QVector<QVector<int>>, QVector<int>> getChannels() const;
    QPair<QVector<QVector<int>>, QVector<int>> initBuffersAndCurves();
    void setupThreads(const QVector<int> &channels, const QString &source);
    void startTimer();

    RuntimeConfig m_cfg;
    NetworkState *m_networkState;
    ChannelAddressState *m_channelState;

    std::shared_ptr<ThreadSafeQueue<QByteArray>> m_rawQueue;
    std::unique_ptr<std::atomic_bool> m_stopFlag;
    DataStore m_dataStore;
    SessionRecorder m_recorder;

    SocketReceiver2 *m_receiver{nullptr};
    ReplayReader *m_replay{nullptr};
    SorterWorker *m_sorter{nullptr};

    bool m_isRunning{false};
    bool m_isPaused{false};
    bool m_saveActive{false};
    QString m_loadedAdcFile;

    QVector<QVector<int>> m_groups;
    QVector<int> m_channels;

    QLabel *m_netLabel{nullptr};
    QLabel *m_netStateLabel{nullptr};
    QLineEdit *m_channelsEdit{nullptr};
    QCheckBox *m_tdmCheckbox{nullptr};
    QCheckBox *m_pauseKeepCaptureCheckbox{nullptr};
    QSpinBox *m_refreshSpin{nullptr};
    QDoubleSpinBox *m_fsSpin{nullptr};
    QSpinBox *m_wavePointsSpin{nullptr};
    QSpinBox *m_fftPointsSpin{nullptr};
    QCheckBox *m_saveCheckbox{nullptr};
    QLineEdit *m_saveDirEdit{nullptr};
    QLineEdit *m_sessionNameEdit{nullptr};
    QLineEdit *m_sessionSuffixEdit{nullptr};
    QDoubleSpinBox *m_replaySpeedSpin{nullptr};
    QPushButton *m_btnGetAddrUnified{nullptr};
    QPushButton *m_btnProbeNetwork{nullptr};

    QPushButton *m_btnLoadFolder{nullptr};
    QPushButton *m_btnStartLive{nullptr};
    QPushButton *m_btnStartReplay{nullptr};
    QPushButton *m_btnPause{nullptr};
    QPushButton *m_btnResume{nullptr};
    QPushButton *m_btnStop{nullptr};

    QLabel *m_statusLabel{nullptr};
    WaveformWidget *m_wavePlot{nullptr};
    WaveformWidget *m_fftPlot{nullptr};
    QPlainTextEdit *m_metricText{nullptr};

    QTimer m_timer;
    QElapsedTimer m_fftUpdateTimer;
};

}  // namespace ccv2
