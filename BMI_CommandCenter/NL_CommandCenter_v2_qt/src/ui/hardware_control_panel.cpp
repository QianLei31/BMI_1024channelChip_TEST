#include "ui/hardware_control_panel.h"

#include <QDateTime>
#include <QGridLayout>
#include <QGroupBox>
#include <QHBoxLayout>
#include <QLabel>
#include <QMessageBox>
#include <QElapsedTimer>
#include <QFormLayout>
#include <QPushButton>
#include <QScrollArea>
#include <QTcpSocket>
#include <QThread>
#include <QVBoxLayout>

#include <algorithm>

#include "core/constants.h"

namespace ccv2 {

HardwareControlPanel::HardwareControlPanel(ConfigManager *cfgMgr,
                                 NetworkState *networkState,
                                 ChannelAddressState *channelState,
                                 QWidget *parent)
    : QWidget(parent), m_cfgMgr(cfgMgr), m_networkState(networkState), m_channelState(channelState) {
    m_appCfg = m_cfgMgr->load();
    loadAttrs();
    buildUi();

    updateNetworkHint(m_networkState->host(), m_networkState->port());
    connect(m_networkState, &NetworkState::endpointChanged, this, &HardwareControlPanel::updateNetworkHint);
}

void HardwareControlPanel::loadAttrs() {
    // Reserved for future field normalization.
}

void HardwareControlPanel::log(const QString &msg, const QString &style) {
    const QString timestamp = QDateTime::currentDateTime().toString(QStringLiteral("HH:mm:ss.zzz"));
    const QString prefix = style.isEmpty()
        ? QStringLiteral("[%1] %2").arg(timestamp, msg)
        : QStringLiteral("[%1] %2 %3").arg(timestamp, style.toUpper(), msg);
    m_console->appendPlainText(prefix);
}

QByteArray HardwareControlPanel::recvTcp(QTcpSocket &socket, int nbytes, int timeoutMs) {
    QByteArray buf;
    qint64 remain = nbytes;
    QElapsedTimer timer;
    timer.start();

    while (remain > 0) {
        if (!socket.waitForReadyRead(10)) {
            if (timeoutMs > 0 && timer.elapsed() > timeoutMs) {
                break;
            }
            continue;
        }
        const QByteArray rx = socket.read(qMin<qint64>(remain, kTcpBuf));
        if (rx.isEmpty()) {
            break;
        }
        buf.append(rx);
        remain -= rx.size();
    }

    return buf;
}

void HardwareControlPanel::singleTcp(const QString &spiCmd, bool showReply) {
    QTcpSocket socket;
    const QString host = m_networkState->host();
    const int port = m_networkState->port();
    socket.connectToHost(host, port);
    if (!socket.waitForConnected(5000)) {
        log(QStringLiteral("Connection Error: ") + socket.errorString(), QStringLiteral("error"));
        return;
    }

    QString clean = spiCmd;
    clean.remove('_');
    clean.remove(' ');
    if (clean.size() % 8 != 0) {
        log(QStringLiteral("Command bits length should be a multiple of 8"), QStringLiteral("error"));
        return;
    }

    QByteArray raw;
    raw.reserve(clean.size() / 8);
    for (int i = 0; i < clean.size(); i += 8) {
        const QString byteBits = clean.mid(i, 8);
        bool ok = false;
        const int v = byteBits.toInt(&ok, 2);
        if (!ok) {
            log(QStringLiteral("Invalid binary command"), QStringLiteral("error"));
            return;
        }
        raw.push_back(static_cast<char>(v));
    }

    const QString msg = QStringLiteral("spi") + QString::fromLatin1(raw.toHex());
    log(QStringLiteral("TX -> %1 @%2:%3").arg(msg, host).arg(port));
    socket.write(msg.toUtf8());
    socket.waitForBytesWritten(1000);

    if (!showReply) {
        socket.disconnectFromHost();
        return;
    }

    const QByteArray data = recvTcp(socket, 12, 5000);
    if (data.isEmpty()) {
        socket.disconnectFromHost();
        return;
    }

    for (int i = 8; i + 4 <= data.size(); i += 4) {
        QByteArray chunk = data.mid(i, 4);
        std::reverse(chunk.begin(), chunk.end());
        const QString bits = QString::number(chunk.toHex().toUInt(nullptr, 16), 2).rightJustified(32, QLatin1Char('0'));
        const QString txt = QStringLiteral("RX <- Code:%1 Addr:%2 Data:%3")
                                .arg(bits.mid(0, 6), bits.mid(6, 10), bits.mid(16));
        log(txt, QStringLiteral("success"));
    }

    socket.disconnectFromHost();
}

void HardwareControlPanel::saveConfig() {
    ConfigMap next;
    for (auto it = m_cfgEdits.cbegin(); it != m_cfgEdits.cend(); ++it) {
        const QStringList parts = it.key().split('/');
        if (parts.size() != 2) {
            continue;
        }
        next[parts[0]][parts[1]] = it.value()->text().trimmed();
    }

    next[QStringLiteral("Network")] = {
        {QStringLiteral("host"), m_networkState->host()},
        {QStringLiteral("port"), QString::number(m_networkState->port())},
    };

    next[QStringLiteral("Stimulator")] = {
        {QStringLiteral("block"), m_stimBlock->text().trimmed()},
        {QStringLiteral("addr_channel"), m_stimAddr->currentText()},
        {QStringLiteral("amplitude"), m_stimAmp->text().trimmed()},
        {QStringLiteral("polarity"), m_stimPolarity->currentText()},
        {QStringLiteral("compensate"), m_stimComp->currentText()},
        {QStringLiteral("step"), m_stimStep->currentText()},
        {QStringLiteral("dac_channel"), m_stimDac->currentText()},
    };

    if (!m_cfgMgr->save(next)) {
        log(QStringLiteral("Save error"), QStringLiteral("error"));
        return;
    }

    m_appCfg = m_cfgMgr->load();
    loadAttrs();
    QMessageBox::information(this, QStringLiteral("OK"), QStringLiteral("Configuration saved"));
}

void HardwareControlPanel::sendDirectSpi() {
    QString cmd = m_spiDirectEdit->text().trimmed();
    cmd.remove('_');
    cmd.remove(' ');
    if (cmd.size() != 32) {
        log(QStringLiteral("Error: length %1, expected 32").arg(cmd.size()), QStringLiteral("error"));
        return;
    }
    singleTcp(cmd);
}

void HardwareControlPanel::seqRecEle16() {
    const QString z(32, QLatin1Char('0'));
    const QStringList cmds = {
        z,
        QStringLiteral("01000000110000001110100000000001"),
        z,
        QStringLiteral("01000100110000000000000000000000"),
        z,
        QStringLiteral("00100000000000000000000000000000"),
    };

    for (const QString &cmd : cmds) {
        singleTcp(cmd, cmd != z);
        QThread::msleep(100);
    }
}

void HardwareControlPanel::runSequence() {
    auto fn = m_seqMap.value(m_seqCombo->currentText());
    if (fn) {
        fn();
    }
}

void HardwareControlPanel::onGetChannelAddress() {
    const QVector<AddressRecord> records = m_channelState->selectedAddressRecords();
    if (records.isEmpty()) {
        m_addrPreview->setPlainText(QStringLiteral("未选择任何通道"));
        log(QStringLiteral("Get Channel Address: no selection"), QStringLiteral("error"));
        return;
    }

    QStringList lines;
    lines << QStringLiteral("Block  Local  Global  SPI(8b+2b)");
    for (const AddressRecord &record : records) {
        lines << QStringLiteral("%1     %2     %3     %4")
                     .arg(record.block, 2, 10, QLatin1Char('0'))
                     .arg(record.localBits)
                     .arg(record.globalChannel, 3, 10, QLatin1Char('0'))
                     .arg(record.addressBits);
    }
    m_addrPreview->setPlainText(lines.join('\n'));
    log(QStringLiteral("Get Channel Address: %1 entries").arg(records.size()));
}

void HardwareControlPanel::updateNetworkHint(const QString &host, int port) {
    if (m_netHintLabel) {
        m_netHintLabel->setText(QStringLiteral("%1:%2").arg(host).arg(port));
    }
}

void HardwareControlPanel::stimSend(const QString &offBit) {
    const QString blk = m_stimBlock->text().trimmed().rightJustified(8, QLatin1Char('0'));
    const QString adr = m_stimAddr->currentText().split(' ').value(0);
    const QString dac = m_stimDac->currentText().split(' ').value(0);
    const QString stp = m_stimStep->currentText().split(' ').value(0);
    const QString cmp = m_stimComp->currentText().split(' ').value(0);
    const QString pol = m_stimPolarity->currentText().split(' ').value(0);
    const QString amp = m_stimAmp->text().trimmed().rightJustified(9, QLatin1Char('0'));
    const QString cmd = QStringLiteral("000110") + blk + adr + offBit + dac + stp + cmp + pol + amp;

    singleTcp(QString(32, QLatin1Char('0')), false);
    QThread::msleep(100);
    singleTcp(cmd, true);
}

void HardwareControlPanel::buildUi() {
    auto *root = new QHBoxLayout(this);

    auto *controlScroll = new QScrollArea;
    controlScroll->setWidgetResizable(true);
    auto *controlWidget = new QWidget;
    auto *controlLayout = new QVBoxLayout(controlWidget);
    controlLayout->setSpacing(10);

    auto *cfgGrp = new QGroupBox(QStringLiteral("Configuration (config.ini)"));
    auto *cfgForm = new QFormLayout(cfgGrp);
    m_netHintLabel = new QLabel;
    cfgForm->addRow(QStringLiteral("Network / endpoint"), m_netHintLabel);

    for (const QString &section : {QStringLiteral("Signal"), QStringLiteral("Paths")}) {
        const ConfigSection sec = m_appCfg.value(section);
        for (auto it = sec.cbegin(); it != sec.cend(); ++it) {
            auto *le = new QLineEdit(it.value());
            const QString key = section + QStringLiteral("/") + it.key();
            m_cfgEdits[key] = le;
            cfgForm->addRow(section + QStringLiteral(" / ") + it.key(), le);
        }
    }
    auto *btnSave = new QPushButton(QStringLiteral("Save Configuration"));
    connect(btnSave, &QPushButton::clicked, this, &HardwareControlPanel::saveConfig);
    cfgForm->addRow(btnSave);
    controlLayout->addWidget(cfgGrp);

    auto *addrGrp = new QGroupBox(QStringLiteral("Channel Address"));
    auto *addrLayout = new QVBoxLayout(addrGrp);
    auto *btnGetAddr = new QPushButton(QStringLiteral("Get Channel Address"));
    connect(btnGetAddr, &QPushButton::clicked, this, &HardwareControlPanel::onGetChannelAddress);
    addrLayout->addWidget(btnGetAddr);
    m_addrPreview = new QPlainTextEdit;
    m_addrPreview->setReadOnly(true);
    m_addrPreview->setMaximumHeight(120);
    addrLayout->addWidget(m_addrPreview);
    controlLayout->addWidget(addrGrp);

    auto *spiGrp = new QGroupBox(QStringLiteral("Advanced SPI Console"));
    auto *spiV = new QVBoxLayout(spiGrp);
    auto *spiWarn = new QLabel(QStringLiteral("Direct SPI commands may change hardware state. Use with caution."));
    spiWarn->setObjectName(QStringLiteral("subtitle"));
    spiWarn->setWordWrap(true);
    spiV->addWidget(spiWarn);
    auto *spiH = new QHBoxLayout;
    m_spiDirectEdit = new QLineEdit;
    m_spiDirectEdit->setPlaceholderText(QStringLiteral("e.g. 00011100000000000000000000000000"));
    auto *btnSend = new QPushButton(QStringLiteral("Send"));
    connect(btnSend, &QPushButton::clicked, this, &HardwareControlPanel::sendDirectSpi);
    spiH->addWidget(m_spiDirectEdit, 1);
    spiH->addWidget(btnSend);
    spiV->addLayout(spiH);
    controlLayout->addWidget(spiGrp);

    auto *globGrp = new QGroupBox(QStringLiteral("Global Commands"));
    auto *gg = new QGridLayout(globGrp);
    const QList<QPair<QString, QString>> cmds = {
        {QStringLiteral("Analog Reset"), QStringLiteral("00011100000000000000000000000000")},
        {QStringLiteral("Analog Remove Reset"), QStringLiteral("00100000000000000000000000000000")},
        {QStringLiteral("Global DAC On"), QStringLiteral("00100100000000000000000000000000")},
        {QStringLiteral("Global DAC Off"), QStringLiteral("00110100000000000000000000000000")},
        {QStringLiteral("SET CBOK LOW"), QStringLiteral("01001000000000000000000000000000")},
        {QStringLiteral("Dummy"), QStringLiteral("00000000000000000000000000000000")},
    };
    for (int i = 0; i < cmds.size(); ++i) {
        auto *btn = new QPushButton(cmds[i].first);
        connect(btn, &QPushButton::clicked, this, [this, i, cmds]() { singleTcp(cmds[i].second, true); });
        gg->addWidget(btn, i / 3, i % 3);
    }
    controlLayout->addWidget(globGrp);

    auto *seqGrp = new QGroupBox(QStringLiteral("Sequence"));
    auto *seqH = new QHBoxLayout(seqGrp);
    m_seqCombo = new QComboBox;
    m_seqMap = {
        {QStringLiteral("REC_ELE16"), [this]() { seqRecEle16(); }},
        {QStringLiteral("Gain -> High"), [this]() { singleTcp(QStringLiteral("00110100000000000000000000000001")); }},
        {QStringLiteral("Gain -> Low"), [this]() { singleTcp(QStringLiteral("00110100000000000000000000000000")); }},
    };
    m_seqCombo->addItems(m_seqMap.keys());
    auto *btnRun = new QPushButton(QStringLiteral("Run"));
    connect(btnRun, &QPushButton::clicked, this, &HardwareControlPanel::runSequence);
    seqH->addWidget(m_seqCombo, 1);
    seqH->addWidget(btnRun);
    controlLayout->addWidget(seqGrp);

    const ConfigSection stimCfg = m_appCfg.value(QStringLiteral("Stimulator"));
    auto *stimGrp = new QGroupBox(QStringLiteral("Stimulator"));
    auto *sf = new QGridLayout(stimGrp);

    m_stimBlock = new QLineEdit(stimCfg.value(QStringLiteral("block"), QStringLiteral("00000000")));
    m_stimAddr = new QComboBox;
    m_stimAddr->addItems({QStringLiteral("00"), QStringLiteral("01"), QStringLiteral("10"), QStringLiteral("11")});
    m_stimAddr->setCurrentText(stimCfg.value(QStringLiteral("addr_channel"), QStringLiteral("00")));
    m_stimAmp = new QLineEdit(stimCfg.value(QStringLiteral("amplitude"), QStringLiteral("000000000")));
    m_stimPolarity = new QComboBox;
    m_stimPolarity->addItems({QStringLiteral("00 (Output 0)"), QStringLiteral("01 (Negative)"), QStringLiteral("10 (Positive)"), QStringLiteral("11 (None)")});
    m_stimPolarity->setCurrentText(stimCfg.value(QStringLiteral("polarity"), QStringLiteral("00 (Output 0)")));
    m_stimDac = new QComboBox;
    m_stimDac->addItems({QStringLiteral("00"), QStringLiteral("01"), QStringLiteral("10"), QStringLiteral("11")});
    m_stimDac->setCurrentText(stimCfg.value(QStringLiteral("dac_channel"), QStringLiteral("00")));
    m_stimComp = new QComboBox;
    m_stimComp->addItems({QStringLiteral("1 (Enable)"), QStringLiteral("0 (Disable)")});
    m_stimComp->setCurrentText(stimCfg.value(QStringLiteral("compensate"), QStringLiteral("0 (Disable)")));
    m_stimStep = new QComboBox;
    m_stimStep->addItems({QStringLiteral("1 (200nA)"), QStringLiteral("0 (4nA)")});
    m_stimStep->setCurrentText(stimCfg.value(QStringLiteral("step"), QStringLiteral("0 (4nA)")));

    sf->addWidget(new QLabel(QStringLiteral("Block")), 0, 0);
    sf->addWidget(m_stimBlock, 0, 1);
    sf->addWidget(new QLabel(QStringLiteral("Addr")), 0, 2);
    sf->addWidget(m_stimAddr, 0, 3);
    sf->addWidget(new QLabel(QStringLiteral("Amplitude")), 1, 0);
    sf->addWidget(m_stimAmp, 1, 1, 1, 3);
    sf->addWidget(new QLabel(QStringLiteral("Polarity")), 2, 0);
    sf->addWidget(m_stimPolarity, 2, 1);
    sf->addWidget(new QLabel(QStringLiteral("DAC")), 2, 2);
    sf->addWidget(m_stimDac, 2, 3);
    sf->addWidget(new QLabel(QStringLiteral("Comp")), 3, 0);
    sf->addWidget(m_stimComp, 3, 1);
    sf->addWidget(new QLabel(QStringLiteral("Step")), 3, 2);
    sf->addWidget(m_stimStep, 3, 3);

    auto *row = new QHBoxLayout;
    auto *btnOut = new QPushButton(QStringLiteral("Output"));
    auto *btnOff = new QPushButton(QStringLiteral("Close"));
    connect(btnOut, &QPushButton::clicked, this, [this]() { stimSend(QStringLiteral("0")); });
    connect(btnOff, &QPushButton::clicked, this, [this]() { stimSend(QStringLiteral("1")); });
    row->addWidget(btnOut);
    row->addWidget(btnOff);
    sf->addLayout(row, 4, 0, 1, 4);
    controlLayout->addWidget(stimGrp);

    controlLayout->addStretch(1);
    controlScroll->setWidget(controlWidget);

    auto *consoleGrp = new QGroupBox(QStringLiteral("Console Output"));
    auto *consoleLayout = new QVBoxLayout(consoleGrp);
    m_console = new QPlainTextEdit;
    m_console->setReadOnly(true);
    m_console->setLineWrapMode(QPlainTextEdit::NoWrap);
    auto *btnClear = new QPushButton(QStringLiteral("Clear"));
    connect(btnClear, &QPushButton::clicked, m_console, &QPlainTextEdit::clear);
    consoleLayout->addWidget(m_console, 1);
    consoleLayout->addWidget(btnClear);

    root->addWidget(controlScroll, 2);
    root->addWidget(consoleGrp, 1);
}

}  // namespace ccv2
