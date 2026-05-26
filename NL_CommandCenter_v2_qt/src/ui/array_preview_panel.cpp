#include "ui/array_preview_panel.h"

#include <QGridLayout>
#include <QHBoxLayout>
#include <QMessageBox>
#include <QSet>
#include <QVBoxLayout>

#include <stdexcept>

#include "core/constants.h"
#include "ui/waveform_widget.h"

namespace ccv2 {

ArrayPreviewPanel::ArrayPreviewPanel(ConfigManager *cfgMgr,
                                                                         NetworkState *networkState,
                                                                         ChannelAddressState *channelState,
                                                                         QWidget *parent)
    : QWidget(parent),
            m_networkState(networkState),
            m_channelState(channelState),
      m_rawQueue(std::make_shared<ThreadSafeQueue<QByteArray>>(128)),
      m_streamState(std::make_shared<RealtimeStreamState>()),
      m_stopFlag(std::make_unique<std::atomic_bool>(false)) {
    const ConfigMap appCfg = cfgMgr->load();
    const ConfigSection net = appCfg.value(QStringLiteral("Network"));
    m_defaultHost = net.value(QStringLiteral("host"), QStringLiteral("localhost"));
    m_samplingRate = appCfg.value(QStringLiteral("Signal")).value(QStringLiteral("sampling_rate"), QStringLiteral("20000")).toDouble();
    m_samplesPerView = qMax(128, static_cast<int>(0.06 * qMax(1.0, m_samplingRate)));

    QVector<int> defaultChannels;
    for (int i = 0; i < 32; ++i) {
        defaultChannels.push_back(i * 8);
    }

    m_streamState->channels = defaultChannels;
    for (int ch : defaultChannels) {
        m_streamState->buffers[ch] = QQueue<double>();
    }

    buildUi(defaultChannels);
    applyViewLengthInternal(false);

    connect(m_networkState, &NetworkState::endpointChanged, this, &ArrayPreviewPanel::onNetworkChanged);
    onNetworkChanged(m_networkState->host(), m_networkState->port());

    connect(&m_refreshTimer, &QTimer::timeout, this, &ArrayPreviewPanel::refresh);
}

void ArrayPreviewPanel::buildUi(const QVector<int> &defaultChannels) {
    auto *root = new QVBoxLayout(this);

    auto *connFrame = new QFrame;
    auto *cf = new QGridLayout(connFrame);

    m_netLabel = new QLabel;
    m_rtCmd = new QLineEdit(QStringLiteral("ctread"));
    m_rtChEdit = new QLineEdit;

    QStringList chs;
    for (int ch : defaultChannels) {
        chs << QString::number(ch);
    }
    m_rtChEdit->setText(chs.join(','));

    cf->addWidget(new QLabel(QStringLiteral("Network")), 0, 0);
    cf->addWidget(m_netLabel, 0, 1, 1, 2);
    cf->addWidget(new QLabel(QStringLiteral("Cmd")), 0, 3);
    cf->addWidget(m_rtCmd, 0, 4, 1, 2);

    m_btnStart = new QPushButton(QStringLiteral("Start"));
    m_btnStop = new QPushButton(QStringLiteral("Stop"));
    m_btnPause = new QPushButton(QStringLiteral("Pause"));
    m_btnResume = new QPushButton(QStringLiteral("Resume"));
    m_btnApply = new QPushButton(QStringLiteral("Apply CH"));
    m_btnGetAddrRt = new QPushButton(QStringLiteral("Get Channel Address"));

    cf->addWidget(m_btnStart, 0, 6);
    cf->addWidget(m_btnStop, 0, 7);
    cf->addWidget(m_btnPause, 0, 8);
    cf->addWidget(m_btnResume, 0, 9);
    cf->addWidget(m_btnGetAddrRt, 0, 10);

    cf->addWidget(new QLabel(QStringLiteral("Channels (1-32 unique, comma-separated)")), 1, 0, 1, 3);
    cf->addWidget(m_rtChEdit, 1, 3, 1, 6);
    cf->addWidget(m_btnApply, 1, 9);

    m_rtPointsSpin = new QSpinBox;
    m_rtPointsSpin->setRange(128, 200000);
    m_rtPointsSpin->setSingleStep(128);
    m_rtPointsSpin->setValue(m_samplesPerView);
    m_rtTimeHint = new QLabel;
    m_btnApplyAxis = new QPushButton(QStringLiteral("Apply X Length"));
    cf->addWidget(new QLabel(QStringLiteral("Draw points")), 2, 0);
    cf->addWidget(m_rtPointsSpin, 2, 1);
    cf->addWidget(m_rtTimeHint, 2, 2, 1, 5);
    cf->addWidget(m_btnApplyAxis, 2, 8, 1, 2);

    m_rtStatus = new QLabel(QStringLiteral("Status: idle"));
    cf->addWidget(m_rtStatus, 3, 0, 1, 11);

    connect(m_btnStart, &QPushButton::clicked, this, &ArrayPreviewPanel::startStream);
    connect(m_btnStop, &QPushButton::clicked, this, &ArrayPreviewPanel::stopStream);
    connect(m_btnPause, &QPushButton::clicked, this, &ArrayPreviewPanel::pauseStream);
    connect(m_btnResume, &QPushButton::clicked, this, &ArrayPreviewPanel::resumeStream);
    connect(m_btnApply, &QPushButton::clicked, this, &ArrayPreviewPanel::applyChannels);
    connect(m_btnApplyAxis, &QPushButton::clicked, this, &ArrayPreviewPanel::applyViewLength);
    connect(m_btnGetAddrRt, &QPushButton::clicked, this, &ArrayPreviewPanel::onGetChannelAddress);

    root->addWidget(connFrame);

    auto *gridW = new QWidget;
    auto *grid = new QGridLayout(gridW);
    grid->setSpacing(4);

    m_waveWidgets.clear();
    for (int i = 0; i < 32; ++i) {
        auto *w = new WaveformWidget(QStringLiteral("CH %1").arg(defaultChannels[i]));
        w->setAxisLabels(QStringLiteral("Time (s)"), QStringLiteral("Voltage (V)"));
        m_waveWidgets.push_back(w);
        grid->addWidget(w, i / 4, i % 4);
    }

    root->addWidget(gridW, 1);
}

QVector<int> ArrayPreviewPanel::parseChannels() const {
    QVector<int> chs;
    const QStringList parts = m_rtChEdit->text().split(',', Qt::SkipEmptyParts);
    for (const QString &p : parts) {
        chs.push_back(p.trimmed().toInt());
    }

    if (chs.size() < 1 || chs.size() > 32) {
        throw std::runtime_error("Need 1-32 channels");
    }

    QSet<int> unique;
    for (int ch : chs) {
        if (ch < 0 || ch >= kChannelsTotal) {
            throw std::runtime_error("Channels must be 0-255");
        }
        unique.insert(ch);
    }
    if (unique.size() != chs.size()) {
        throw std::runtime_error("Channels must be unique");
    }
    return chs;
}

void ArrayPreviewPanel::applyChannels() {
    applyChannelsInternal();
}

bool ArrayPreviewPanel::applyChannelsInternal() {
    QVector<int> chs;
    try {
        chs = parseChannels();
    } catch (const std::exception &exc) {
        QMessageBox::warning(this, QStringLiteral("Channel Error"), QString::fromUtf8(exc.what()));
        return false;
    }

    {
        QMutexLocker locker(&m_streamState->lock);
        m_streamState->channels = chs;
        m_streamState->maxSamples = m_samplesPerView;
        m_streamState->buffers.clear();
        for (int ch : chs) {
            m_streamState->buffers[ch] = QQueue<double>();
        }
    }

    for (int i = 0; i < chs.size(); ++i) {
        m_waveWidgets[i]->setTitle(QStringLiteral("CH %1").arg(chs[i]));
        m_waveWidgets[i]->show();
    }
    for (int i = chs.size(); i < m_waveWidgets.size(); ++i) {
        m_waveWidgets[i]->setData({});
        m_waveWidgets[i]->hide();
    }
    m_rtStatus->setText(QStringLiteral("Status: channels updated"));
    return true;
}

void ArrayPreviewPanel::applyViewLength() {
    applyViewLengthInternal(true);
}

bool ArrayPreviewPanel::applyViewLengthInternal(bool showMessage) {
    if (!m_rtPointsSpin) {
        return true;
    }

    m_samplesPerView = qMax(128, m_rtPointsSpin->value());
    {
        QMutexLocker locker(&m_streamState->lock);
        m_streamState->maxSamples = m_samplesPerView;
        for (int ch : m_streamState->channels) {
            QQueue<double> old = m_streamState->buffers.value(ch);
            while (old.size() > m_samplesPerView) {
                old.dequeue();
            }
            m_streamState->buffers[ch] = old;
        }
    }

    const double seconds = static_cast<double>(m_samplesPerView - 1) / qMax(1.0, m_samplingRate);
    for (WaveformWidget *w : m_waveWidgets) {
        w->setXRange(0.0, seconds);
        w->setYRange(0.0, 1.8);
    }

    if (m_refreshTimer.isActive()) {
        m_refreshTimer.start(refreshIntervalMs());
    }
    updateTimeHint();
    if (showMessage && m_rtStatus) {
        m_rtStatus->setText(QStringLiteral("Status: x length updated"));
    }
    return true;
}

int ArrayPreviewPanel::refreshIntervalMs() const {
    if (m_samplesPerView <= 8000) {
        return 100;
    }
    if (m_samplesPerView <= 30000) {
        return 160;
    }
    if (m_samplesPerView <= 70000) {
        return 220;
    }
    return 300;
}

void ArrayPreviewPanel::updateTimeHint() {
    if (!m_rtTimeHint) {
        return;
    }
    const double timeMs = static_cast<double>(m_samplesPerView) / qMax(1.0, m_samplingRate) * 1000.0;
    const double refreshHz = 1000.0 / static_cast<double>(qMax(1, refreshIntervalMs()));
    m_rtTimeHint->setText(QStringLiteral("X span: %1 ms, refresh: %2 Hz")
                              .arg(timeMs, 0, 'f', 2)
                              .arg(refreshHz, 0, 'f', 1));
}

void ArrayPreviewPanel::startStream() {
    stopStream();
    if (!applyViewLengthInternal(false)) {
        return;
    }
    if (!applyChannelsInternal()) {
        return;
    }

    const QString host = m_networkState->host();
    const int port = m_networkState->port();

    m_stopFlag = std::make_unique<std::atomic_bool>(false);
    m_rawQueue->clear();

    m_receiver = new TcpReceiver(host, port, m_rtCmd->text().trimmed(), m_rawQueue, m_stopFlag.get(), this);
    m_sorter = new DataSorter(m_rawQueue, m_streamState, m_stopFlag.get(), this);

    m_receiver->start();
    m_sorter->start();

    m_paused = false;
    m_streaming = true;
    m_refreshTimer.start(refreshIntervalMs());
    m_rtStatus->setText(QStringLiteral("Status: streaming %1:%2").arg(host).arg(port));
}

void ArrayPreviewPanel::stopStream() {
    m_streaming = false;
    if (m_refreshTimer.isActive()) {
        m_refreshTimer.stop();
    }
    if (m_stopFlag) {
        m_stopFlag->store(true);
    }

    if (m_receiver) {
        m_receiver->wait(1000);
        m_receiver->deleteLater();
        m_receiver = nullptr;
    }
    if (m_sorter) {
        m_sorter->wait(1000);
        m_sorter->deleteLater();
        m_sorter = nullptr;
    }

    m_rtStatus->setText(QStringLiteral("Status: stopped"));
}

void ArrayPreviewPanel::pauseStream() {
    m_paused = true;
    m_rtStatus->setText(QStringLiteral("Status: paused"));
}

void ArrayPreviewPanel::resumeStream() {
    m_paused = false;
    m_rtStatus->setText(QStringLiteral("Status: streaming"));
}

void ArrayPreviewPanel::refresh() {
    if (!m_streaming) {
        return;
    }
    if (m_paused) {
        return;
    }

    QVector<int> chs;
    QVector<QVector<double>> samples;
    {
        QMutexLocker locker(&m_streamState->lock);
        chs = m_streamState->channels;
        samples.reserve(chs.size());
        for (int ch : chs) {
            auto it = m_streamState->buffers.constFind(ch);
            if (it == m_streamState->buffers.cend()) {
                samples.push_back({});
                continue;
            }
            const QQueue<double> &q = it.value();
            const int count = qMin(m_samplesPerView, q.size());
            QVector<double> data;
            data.reserve(count);
            const int start = q.size() - count;
            for (int j = start; j < q.size(); ++j) {
                data.push_back(q.at(j));
            }
            samples.push_back(data);
        }
    }

    for (int i = 0; i < chs.size() && i < m_waveWidgets.size(); ++i) {
        m_waveWidgets[i]->setData(samples.value(i));
    }
}

void ArrayPreviewPanel::shutdown() {
    stopStream();
}

void ArrayPreviewPanel::setWaveTheme(const QMap<QString, QString> &palette) {
    for (WaveformWidget *w : m_waveWidgets) {
        w->setPaletteColors(palette);
    }
}

void ArrayPreviewPanel::onNetworkChanged(const QString &host, int port) {
    if (m_netLabel) {
        m_netLabel->setText(QStringLiteral("%1:%2").arg(host).arg(port));
    }
}

void ArrayPreviewPanel::onGetChannelAddress() {
    QVector<int> channels = m_channelState->selectedGlobalChannels();
    if (channels.isEmpty()) {
        QMessageBox::warning(this, QStringLiteral("Get Channel Address"), QStringLiteral("请先在1024通道分布页面选择通道"));
        return;
    }
    if (channels.size() > 32) {
        channels = channels.mid(0, 32);
        m_rtStatus->setText(QStringLiteral("Status: got channels from address map (truncated to 32)"));
    } else {
        m_rtStatus->setText(QStringLiteral("Status: got channels from address map"));
    }

    QStringList txt;
    for (int ch : channels) {
        txt << QString::number(ch);
    }
    m_rtChEdit->setText(txt.join(','));
    applyChannelsInternal();
}

}  // namespace ccv2
