#include "ui/channel_analyzer_panel.h"

#include <QDateTime>
#include <QFileDialog>
#include <QFile>
#include <QFrame>
#include <QColor>
#include <QGridLayout>
#include <QGroupBox>
#include <QHBoxLayout>
#include <QLayoutItem>
#include <QMessageBox>
#include <QSet>
#include <QSizePolicy>
#include <QSplitter>
#include <QVBoxLayout>

#include <algorithm>
#include <cmath>
#include <QTcpSocket>
#include <stdexcept>

#include "core/constants.h"
#include "signal/sndr_calculator.h"
#include "ui/waveform_widget.h"

namespace ccv2 {

namespace {

int floorPowerOfTwo(int value) {
    int p = 1;
    while (p <= value / 2) {
        p *= 2;
    }
    return qMax(256, p);
}

int fftRefreshIntervalMs(int fftPoints) {
    return qBound(500, fftPoints / 16, 1500);
}

void setGridLabelText(QGridLayout *layout, int row, int column, const QString &text) {
    QLayoutItem *item = layout->itemAtPosition(row, column);
    if (!item || !item->widget()) {
        return;
    }
    if (auto *label = qobject_cast<QLabel *>(item->widget())) {
        label->setText(text);
    }
}

}  // namespace

ChannelAnalyzerPanel::ChannelAnalyzerPanel(ConfigManager *cfgMgr,
                                                                                 NetworkState *networkState,
                                                                                 ChannelAddressState *channelState,
                                                                                 QWidget *parent)
    : QWidget(parent),
            m_networkState(networkState),
            m_channelState(channelState),
      m_rawQueue(std::make_shared<ThreadSafeQueue<QByteArray>>(200)),
      m_stopFlag(std::make_unique<std::atomic_bool>(false)) {
    const ConfigMap parser = cfgMgr->load();
    m_cfg.host = parser.value(QStringLiteral("Network")).value(QStringLiteral("host"), QStringLiteral("localhost"));
    m_cfg.port = parser.value(QStringLiteral("Network")).value(QStringLiteral("port"), QStringLiteral("10086")).toInt();
    m_cfg.samplingRate = parser.value(QStringLiteral("Signal")).value(QStringLiteral("sampling_rate"), QStringLiteral("20000")).toDouble();
    m_cfg.fftPoints = parser.value(QStringLiteral("Signal")).value(QStringLiteral("fft_points"), QStringLiteral("16384")).toInt();
    m_cfg.saveDir = parser.value(QStringLiteral("Paths")).value(QStringLiteral("save_dir"), QStringLiteral("d:/ADC_data"));

    auto *main = new QHBoxLayout(this);
    main->setContentsMargins(8, 8, 8, 8);

    auto *control = new QGroupBox(QStringLiteral("Unified Monitor Controls"));
    control->setMinimumWidth(320);
    control->setMaximumWidth(460);
    control->setSizePolicy(QSizePolicy::Preferred, QSizePolicy::Expanding);
    auto *form = new QGridLayout(control);
    form->setAlignment(Qt::AlignTop);

    int row = 0;
    auto *netCard = new QFrame;
    netCard->setObjectName(QStringLiteral("networkCard"));
    auto *netCardGrid = new QGridLayout(netCard);
    netCardGrid->addWidget(new QLabel(QStringLiteral("统一网络")), 0, 0);
    setGridLabelText(netCardGrid, 0, 0, QStringLiteral("统一网络"));
    m_netLabel = new QLabel;
    netCardGrid->addWidget(m_netLabel, 0, 1);
    m_netStateLabel = new QLabel(QStringLiteral("待检测"));
    m_netStateLabel->setText(QStringLiteral("待检测"));
    m_netStateLabel->setObjectName(QStringLiteral("networkStateBadge"));
    netCardGrid->addWidget(m_netStateLabel, 0, 2);
    m_btnProbeNetwork = new QPushButton(QStringLiteral("检查连接"));
    m_btnProbeNetwork->setText(QStringLiteral("检查连接"));
    netCardGrid->addWidget(m_btnProbeNetwork, 0, 3);
    auto *tipLabel = new QLabel(QStringLiteral("提示: Host/Port 在窗口顶部统一设置，这里只显示和检测"));
    tipLabel->setText(QStringLiteral("提示: Host/Port 在窗口顶部统一设置，这里只显示和检测"));
    tipLabel->setWordWrap(true);
    netCardGrid->addWidget(tipLabel, 1, 0, 1, 4);
    netCardGrid->setColumnStretch(1, 1);
    form->addWidget(netCard, row, 0, 1, 4);

    row += 1;
    form->addWidget(new QLabel(QStringLiteral("通道")), row, 0);
    m_channelsEdit = new QLineEdit(QStringLiteral("239,240,241,242,243"));
    m_channelsEdit->setToolTip(QStringLiteral("普通模式: 239,240,241  |  TDM分组: 239,240;241,242"));
    m_channelsEdit->setToolTip(QStringLiteral("普通模式: 239,240,241  |  TDM分组: 239,240;241,242"));
    form->addWidget(m_channelsEdit, row, 1, 1, 2);
    m_btnGetAddrUnified = new QPushButton(QStringLiteral("Get Channel Address"));
    form->addWidget(m_btnGetAddrUnified, row, 3);

    row += 1;
    m_tdmCheckbox = new QCheckBox(QStringLiteral("TDM分组显示"));
    m_tdmCheckbox->setText(QStringLiteral("TDM分组显示"));
    form->addWidget(m_tdmCheckbox, row, 0, 1, 2);
    m_pauseKeepCaptureCheckbox = new QCheckBox(QStringLiteral("暂停时继续采集"));
    m_pauseKeepCaptureCheckbox->setText(QStringLiteral("暂停时继续采集"));
    m_pauseKeepCaptureCheckbox->setChecked(true);
    form->addWidget(m_pauseKeepCaptureCheckbox, row, 2, 1, 2);

    row += 1;
    form->addWidget(new QLabel(QStringLiteral("刷新率(Hz)")), row, 0);
    setGridLabelText(form, row, 0, QStringLiteral("刷新率(Hz)"));
    m_refreshSpin = new QSpinBox;
    m_refreshSpin->setRange(1, 60);
    m_refreshSpin->setValue(10);
    form->addWidget(m_refreshSpin, row, 1);

    form->addWidget(new QLabel(QStringLiteral("采样率(Hz)")), row, 2);
    setGridLabelText(form, row, 2, QStringLiteral("采样率(Hz)"));
    m_fsSpin = new QDoubleSpinBox;
    m_fsSpin->setRange(1000.0, 1000000.0);
    m_fsSpin->setDecimals(2);
    m_fsSpin->setValue(m_cfg.samplingRate);
    form->addWidget(m_fsSpin, row, 3);

    row += 1;
    form->addWidget(new QLabel(QStringLiteral("波形点数")), row, 0);
    setGridLabelText(form, row, 0, QStringLiteral("波形点数"));
    m_wavePointsSpin = new QSpinBox;
    m_wavePointsSpin->setRange(256, 262144);
    m_wavePointsSpin->setSingleStep(256);
    m_wavePointsSpin->setValue(8000);
    form->addWidget(m_wavePointsSpin, row, 1);

    form->addWidget(new QLabel(QStringLiteral("FFT点数")), row, 2);
    setGridLabelText(form, row, 2, QStringLiteral("FFT点数"));
    m_fftPointsSpin = new QSpinBox;
    m_fftPointsSpin->setRange(256, 262144);
    m_fftPointsSpin->setSingleStep(256);
    m_fftPointsSpin->setValue(m_cfg.fftPoints);
    form->addWidget(m_fftPointsSpin, row, 3);

    row += 1;
    m_saveCheckbox = new QCheckBox(QStringLiteral("保存原始流(ADC_DATA.bin)"));
    m_saveCheckbox->setText(QStringLiteral("保存原始流(ADC_DATA.bin)"));
    form->addWidget(m_saveCheckbox, row, 0, 1, 2);
    form->addWidget(new QLabel(QStringLiteral("保存目录")), row, 2);
    setGridLabelText(form, row, 2, QStringLiteral("保存目录"));
    m_saveDirEdit = new QLineEdit(m_cfg.saveDir);
    form->addWidget(m_saveDirEdit, row, 3);

    row += 1;
    form->addWidget(new QLabel(QStringLiteral("会话名")), row, 0);
    setGridLabelText(form, row, 0, QStringLiteral("会话名"));
    m_sessionNameEdit = new QLineEdit;
    form->addWidget(m_sessionNameEdit, row, 1);
    form->addWidget(new QLabel(QStringLiteral("后缀")), row, 2);
    setGridLabelText(form, row, 2, QStringLiteral("后缀"));
    m_sessionSuffixEdit = new QLineEdit;
    form->addWidget(m_sessionSuffixEdit, row, 3);

    row += 1;
    auto *refreshNameButton = new QPushButton(QStringLiteral("刷新时间前缀"));
    refreshNameButton->setText(QStringLiteral("刷新时间前缀"));
    form->addWidget(refreshNameButton, row, 0);
    m_btnLoadFolder = new QPushButton(QStringLiteral("加载历史文件夹"));
    m_btnLoadFolder->setText(QStringLiteral("加载历史文件夹"));
    form->addWidget(m_btnLoadFolder, row, 1);

    m_replaySpeedSpin = new QDoubleSpinBox;
    m_replaySpeedSpin->setRange(0.1, 10.0);
    m_replaySpeedSpin->setSingleStep(0.1);
    m_replaySpeedSpin->setValue(1.0);
    form->addWidget(m_replaySpeedSpin, row, 2);
    form->addWidget(new QLabel(QStringLiteral("回放倍速")), row, 3);

    row += 1;
    m_btnStartLive = new QPushButton(QStringLiteral("开始实时"));
    m_btnStartLive->setText(QStringLiteral("开始实时"));
    setGridLabelText(form, row - 1, 3, QStringLiteral("回放倍速"));
    form->addWidget(m_btnStartLive, row, 0);
    m_btnStartReplay = new QPushButton(QStringLiteral("开始回放"));
    m_btnStartReplay->setText(QStringLiteral("开始回放"));
    form->addWidget(m_btnStartReplay, row, 1);
    m_btnPause = new QPushButton(QStringLiteral("暂停"));
    m_btnPause->setText(QStringLiteral("暂停"));
    form->addWidget(m_btnPause, row, 2);
    m_btnResume = new QPushButton(QStringLiteral("继续"));
    m_btnResume->setText(QStringLiteral("继续"));
    form->addWidget(m_btnResume, row, 3);

    row += 1;
    m_btnStop = new QPushButton(QStringLiteral("停止"));
    form->addWidget(m_btnStop, row, 0);
    m_statusLabel = new QLabel(QStringLiteral("状态: Idle"));
    form->addWidget(m_statusLabel, row, 1, 1, 3);

    auto *plots = new QWidget;
    auto *plotsLayout = new QVBoxLayout(plots);
    plotsLayout->setContentsMargins(6, 0, 0, 0);
    plots->setMinimumWidth(760);
    m_wavePlot = new WaveformWidget(QStringLiteral("实时波形"));
    m_wavePlot->setYRange(0.0, 1.8);
    m_wavePlot->setAxisLabels(QStringLiteral("Time (s)"), QStringLiteral("Voltage (V)"));
    m_wavePlot->setMaxRenderPoints(0);
    m_wavePlot->setMinimumHeight(260);
    plotsLayout->addWidget(m_wavePlot, 1);

    m_fftPlot = new WaveformWidget(QStringLiteral("实时FFT"));
    m_fftPlot->setYRange(-180.0, 20.0);
    m_fftPlot->setAxisLabels(QStringLiteral("Frequency (Hz)"), QStringLiteral("Amplitude (dB)"));
    m_fftPlot->setMaxRenderPoints(0);
    m_fftPlot->setMinimumHeight(260);
    plotsLayout->addWidget(m_fftPlot, 1);

    m_metricText = new QPlainTextEdit;
    m_metricText->setReadOnly(true);
    m_metricText->setMaximumHeight(96);
    plotsLayout->addWidget(m_metricText);

    auto *splitter = new QSplitter(Qt::Horizontal);
    splitter->setChildrenCollapsible(false);
    splitter->addWidget(control);
    splitter->addWidget(plots);
    splitter->setStretchFactor(0, 0);
    splitter->setStretchFactor(1, 1);
    splitter->setSizes({400, 1200});
    main->addWidget(splitter, 1);

    connect(&m_timer, &QTimer::timeout, this, &ChannelAnalyzerPanel::updatePlots);
    connect(refreshNameButton, &QPushButton::clicked, this, &ChannelAnalyzerPanel::rebuildSessionName);
    connect(m_sessionSuffixEdit, &QLineEdit::textChanged, this, &ChannelAnalyzerPanel::rebuildSessionName);
    connect(m_btnLoadFolder, &QPushButton::clicked, this, &ChannelAnalyzerPanel::loadFolder);
    connect(m_btnStartLive, &QPushButton::clicked, this, &ChannelAnalyzerPanel::startLive);
    connect(m_btnStartReplay, &QPushButton::clicked, this, &ChannelAnalyzerPanel::startReplay);
    connect(m_btnPause, &QPushButton::clicked, this, &ChannelAnalyzerPanel::pauseView);
    connect(m_btnResume, &QPushButton::clicked, this, &ChannelAnalyzerPanel::resumeView);
    connect(m_btnStop, &QPushButton::clicked, this, &ChannelAnalyzerPanel::stopAll);
    connect(m_btnGetAddrUnified, &QPushButton::clicked, this, &ChannelAnalyzerPanel::onGetChannelAddress);
    connect(m_btnProbeNetwork, &QPushButton::clicked, this, &ChannelAnalyzerPanel::checkNetworkConnectivity);
    connect(m_networkState, &NetworkState::endpointChanged, this, &ChannelAnalyzerPanel::onNetworkChanged);

    rebuildSessionName();
    onNetworkChanged(m_networkState->host(), m_networkState->port());
}

QPair<QVector<QVector<int>>, QVector<int>> ChannelAnalyzerPanel::parseChannelGroups(const QString &text) const {
    QVector<QVector<int>> groups;
    QVector<int> flat;
    const QString t = text.trimmed();
    if (t.isEmpty()) {
        return {QVector<QVector<int>>{QVector<int>{243}}, QVector<int>{243}};
    }

    const QStringList groupTexts = t.split(';', Qt::SkipEmptyParts);
    QSet<int> seenGlobal;
    for (const QString &grp : groupTexts) {
        const QStringList items = grp.split(',', Qt::SkipEmptyParts);
        QVector<int> g;
        for (const QString &it : items) {
            bool ok = false;
            const int ch = it.trimmed().toInt(&ok);
            if (!ok || ch < 0 || ch >= kChannelsTotal) {
                throw std::runtime_error("channel out of range");
            }
            if (seenGlobal.contains(ch)) {
                throw std::runtime_error("duplicate channel");
            }
            seenGlobal.insert(ch);
            g.push_back(ch);
            flat.push_back(ch);
        }
        if (!g.isEmpty()) {
            groups.push_back(g);
        }
    }

    if (groups.isEmpty()) {
        throw std::runtime_error("no valid channel");
    }

    QVector<int> unique;
    QSet<int> seen;
    for (int ch : flat) {
        if (!seen.contains(ch)) {
            seen.insert(ch);
            unique.push_back(ch);
        }
    }
    return {groups, unique};
}

QPair<QVector<QVector<int>>, QVector<int>> ChannelAnalyzerPanel::getChannels() const {
    return parseChannelGroups(m_channelsEdit->text());
}

QPair<QVector<QVector<int>>, QVector<int>> ChannelAnalyzerPanel::initBuffersAndCurves() {
    auto gv = getChannels();
    m_groups = gv.first;
    m_channels = gv.second;

    const int maxPoints = qMax(m_wavePointsSpin->value(), m_fftPointsSpin->value());
    const int capacity = qMax(maxPoints * 8, 65536);
    m_dataStore.reset(m_channels, capacity);

    return gv;
}

void ChannelAnalyzerPanel::setupThreads(const QVector<int> &channels, const QString &source) {
    m_stopFlag = std::make_unique<std::atomic_bool>(false);
    m_rawQueue->clear();

    if (m_saveCheckbox->isChecked() && source == QStringLiteral("live")) {
        const QString folderName = m_sessionNameEdit->text().trimmed().isEmpty()
                                       ? QDateTime::currentDateTime().toString(QStringLiteral("MMdd_hhmm"))
                                       : m_sessionNameEdit->text().trimmed();
        const QString session = m_recorder.start(m_saveDirEdit->text().trimmed(), folderName);
        m_saveActive = !session.isEmpty();
        if (m_saveActive) {
            m_statusLabel->setText(QStringLiteral("状态: 保存到 %1").arg(session));
        }
    } else {
        m_saveActive = false;
    }

    m_sorter = new SorterWorker(
        m_rawQueue,
        &m_dataStore,
        channels,
        &m_recorder,
        [this]() { return m_saveActive; },
        [this]() { return (!m_isPaused) || m_pauseKeepCaptureCheckbox->isChecked(); },
        m_stopFlag.get(),
        this);
    m_sorter->start();

    if (source == QStringLiteral("live")) {
        m_receiver = new SocketReceiver2(m_networkState->host(), m_networkState->port(), m_rawQueue, m_stopFlag.get(), this);
        m_receiver->start();
    } else {
        m_replay = new ReplayReader(m_loadedAdcFile, m_rawQueue, m_stopFlag.get(), m_fsSpin->value(), m_replaySpeedSpin->value(), this);
        m_replay->start();
    }
}

void ChannelAnalyzerPanel::startLive() {
    if (m_isRunning) {
        m_statusLabel->setText(QStringLiteral("状态: 已在运行"));
        return;
    }

    try {
        auto gv = initBuffersAndCurves();
        setupThreads(gv.second, QStringLiteral("live"));
    } catch (const std::exception &exc) {
        m_statusLabel->setText(QStringLiteral("状态: 通道参数错误: ") + QString::fromUtf8(exc.what()));
        return;
    }

    startTimer();
    m_isRunning = true;
    m_isPaused = false;
    m_statusLabel->setText(QStringLiteral("状态: 实时采集中"));
}

void ChannelAnalyzerPanel::startReplay() {
    if (m_isRunning) {
        m_statusLabel->setText(QStringLiteral("状态: 请先停止当前任务"));
        return;
    }
    if (m_loadedAdcFile.isEmpty()) {
        m_statusLabel->setText(QStringLiteral("状态: 请先加载包含 ADC_DATA.bin 的目录"));
        return;
    }

    try {
        auto gv = initBuffersAndCurves();
        setupThreads(gv.second, QStringLiteral("replay"));
    } catch (const std::exception &exc) {
        m_statusLabel->setText(QStringLiteral("状态: 通道参数错误: ") + QString::fromUtf8(exc.what()));
        return;
    }

    startTimer();
    m_isRunning = true;
    m_isPaused = false;
    m_statusLabel->setText(QStringLiteral("状态: 历史回放中"));
}

void ChannelAnalyzerPanel::startTimer() {
    const int intervalMs = 1000 / qMax(1, m_refreshSpin->value());
    m_fftUpdateTimer.invalidate();
    m_timer.start(intervalMs);
}

void ChannelAnalyzerPanel::pauseView() {
    if (m_isRunning) {
        m_isPaused = true;
        m_statusLabel->setText(QStringLiteral("状态: 已暂停"));
    }
}

void ChannelAnalyzerPanel::resumeView() {
    if (m_isRunning) {
        m_isPaused = false;
        m_statusLabel->setText(QStringLiteral("状态: 已继续"));
    }
}

void ChannelAnalyzerPanel::stopAll() {
    if (m_stopFlag) {
        m_stopFlag->store(true);
    }
    if (m_timer.isActive()) {
        m_timer.stop();
    }

    m_isRunning = false;
    m_isPaused = false;

    if (m_receiver) {
        m_receiver->wait(1500);
        m_receiver->deleteLater();
        m_receiver = nullptr;
    }
    if (m_replay) {
        m_replay->wait(1500);
        m_replay->deleteLater();
        m_replay = nullptr;
    }
    if (m_sorter) {
        m_sorter->wait(1500);
        m_sorter->deleteLater();
        m_sorter = nullptr;
    }

    m_saveActive = false;
    m_recorder.stop();
    m_statusLabel->setText(QStringLiteral("状态: 已停止"));
}

void ChannelAnalyzerPanel::rebuildSessionName() {
    const QString prefix = QDateTime::currentDateTime().toString(QStringLiteral("MMdd_hhmm"));
    const QString suffix = m_sessionSuffixEdit->text().trimmed();
    m_sessionNameEdit->setText(suffix.isEmpty() ? prefix : prefix + QStringLiteral("_") + suffix);
}

void ChannelAnalyzerPanel::loadFolder() {
    const QString folder = QFileDialog::getExistingDirectory(this, QStringLiteral("选择历史会话目录"), m_saveDirEdit->text());
    if (folder.isEmpty()) {
        return;
    }

    const QString adc = folder + QStringLiteral("/ADC_DATA.bin");
    if (!QFile::exists(adc)) {
        m_statusLabel->setText(QStringLiteral("状态: 所选目录没有 ADC_DATA.bin"));
        return;
    }

    m_loadedAdcFile = adc;
    m_statusLabel->setText(QStringLiteral("状态: 已加载 %1").arg(adc));
}

void ChannelAnalyzerPanel::updatePlots() {
    if (!m_isRunning) {
        return;
    }
    if (m_stopFlag && m_stopFlag->load()) {
        stopAll();
        return;
    }
    if (m_isPaused) {
        return;
    }

    if (m_channels.isEmpty()) {
        return;
    }

    const int waveN = m_wavePointsSpin->value();
    const int fftN = floorPowerOfTwo(m_fftPointsSpin->value());
    const double fs = m_fsSpin->value();
    const bool doFft = !m_fftUpdateTimer.isValid() ||
                       m_fftUpdateTimer.elapsed() >= fftRefreshIntervalMs(fftN);
    if (doFft) {
        m_fftUpdateTimer.restart();
    }
    m_wavePlot->setXRange(0.0, static_cast<double>(qMax(1, waveN - 1)) / qMax(1.0, fs));
    m_fftPlot->setXRange(0.0, fs / 2.0);

    QVector<WaveformWidget::PlotSeries> waveSeries;
    QVector<WaveformWidget::PlotSeries> fftSeries;
    QStringList metricsLines;

    int colorIdx = 0;
    for (int gIdx = 0; gIdx < m_groups.size(); ++gIdx) {
        const QVector<int> &grp = m_groups[gIdx];
        for (int ch : grp) {
            RingBuffer *buf = m_dataStore.buffer(ch);
            if (!buf) {
                continue;
            }

            auto wavePair = buf->getLatest(waveN);
            const QVector<qint32> &waveRaw = wavePair.second;
            if (!waveRaw.isEmpty()) {
                QVector<double> waveV;
                waveV.reserve(waveRaw.size());
                for (qint32 v : waveRaw) {
                    waveV.push_back(static_cast<double>(v) / static_cast<double>(1 << kAdcBits) * kVref);
                }

                WaveformWidget::PlotSeries s;
                s.data = waveV;
                s.color = QColor::fromHsv((colorIdx * 47) % 360, 220, 255);
                waveSeries.push_back(s);
            }

            if (!doFft) {
                colorIdx++;
                continue;
            }

            auto fftPair = buf->getLatest(fftN);
            const QVector<qint32> &fftRaw = fftPair.second;
            if (fftRaw.isEmpty()) {
                colorIdx++;
                continue;
            }

            QVector<double> fftV;
            fftV.reserve(fftRaw.size());
            for (qint32 v : fftRaw) {
                fftV.push_back(static_cast<double>(v) / static_cast<double>(1 << kAdcBits) * kVref);
            }

            const SndrResult r = calSndr(fftV, fs, fs / 2.0, QStringLiteral("hann"));
            if (r.ok) {
                QVector<double> fftDb;
                fftDb.reserve(r.fftData.size());
                for (double p : r.fftData) {
                    fftDb.push_back(10.0 * std::log10(std::max(p, 1e-18)));
                }

                WaveformWidget::PlotSeries fsSeries;
                fsSeries.data = fftDb;
                fsSeries.color = QColor::fromHsv((colorIdx * 47) % 360, 220, 255);
                fftSeries.push_back(fsSeries);

                if (!m_channels.isEmpty() && ch == m_channels.first()) {
                    metricsLines << QStringLiteral("CH%1 Freq=%2Hz | SNDR=%3dB | ENOB=%4bit | THD=%5dB | IRN=%6uVrms")
                                        .arg(ch)
                                        .arg(r.fin, 0, 'f', 2)
                                        .arg(r.sndrDb, 0, 'f', 2)
                                        .arg(r.enob, 0, 'f', 2)
                                        .arg(r.thdDb, 0, 'f', 2)
                                        .arg(r.irn / 60.0 * 1e6, 0, 'f', 2);
                }
            } else if (!m_channels.isEmpty() && ch == m_channels.first()) {
                metricsLines << QStringLiteral("CH%1 FFT错误: %2").arg(ch).arg(r.error);
            }

            colorIdx++;
        }
    }

    if (!waveSeries.isEmpty()) {
        m_wavePlot->setSeries(waveSeries);
    }
    if (doFft && !fftSeries.isEmpty()) {
        m_fftPlot->setSeries(fftSeries);
    }
    if (doFft) {
        m_metricText->setPlainText(metricsLines.join('\n'));
    }
}

void ChannelAnalyzerPanel::shutdown() {
    stopAll();
}

void ChannelAnalyzerPanel::setPlotTheme(const QString &plotBg, const QString &plotAxis) {
    QMap<QString, QString> palette;
    palette.insert(QStringLiteral("bg"), plotBg);
    palette.insert(QStringLiteral("title"), plotAxis);
    palette.insert(QStringLiteral("grid"), plotAxis);
    palette.insert(QStringLiteral("wave"), plotAxis);
    palette.insert(QStringLiteral("axis"), plotAxis);
    m_wavePlot->setPaletteColors(palette);
    m_fftPlot->setPaletteColors(palette);
}

void ChannelAnalyzerPanel::onNetworkChanged(const QString &host, int port) {
    m_netLabel->setText(QStringLiteral("%1:%2").arg(host).arg(port));
    m_netStateLabel->setText(QStringLiteral("已同步"));
}

void ChannelAnalyzerPanel::onGetChannelAddress() {
    QVector<int> channels = m_channelState->selectedGlobalChannels();
    if (channels.isEmpty()) {
        QMessageBox::warning(this, QStringLiteral("Get Channel Address"), QStringLiteral("请先在1024通道分布页面选择通道"));
        return;
    }
    QStringList text;
    for (int ch : channels) {
        text << QString::number(ch);
    }
    m_channelsEdit->setText(text.join(','));
    m_statusLabel->setText(QStringLiteral("状态: 已从通道分布载入通道"));
}

void ChannelAnalyzerPanel::checkNetworkConnectivity() {
    QTcpSocket socket;
    socket.connectToHost(m_networkState->host(), m_networkState->port());
    if (socket.waitForConnected(800)) {
        m_netStateLabel->setText(QStringLiteral("可连接"));
        m_statusLabel->setText(QStringLiteral("状态: 网络连接正常 %1:%2").arg(m_networkState->host()).arg(m_networkState->port()));
    } else {
        m_netStateLabel->setText(QStringLiteral("不可连接"));
        m_statusLabel->setText(QStringLiteral("状态: 网络检测失败 %1:%2 (%3)")
                                   .arg(m_networkState->host())
                                   .arg(m_networkState->port())
                                   .arg(socket.errorString()));
    }
}

}  // namespace ccv2
