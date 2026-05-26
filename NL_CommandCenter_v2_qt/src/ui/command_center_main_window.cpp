#include "ui/command_center_main_window.h"

#include <QCloseEvent>
#include <QGuiApplication>
#include <QHBoxLayout>
#include <QLabel>
#include <QListWidget>
#include <QMessageBox>
#include <QScreen>
#include <QSplitter>
#include <QVBoxLayout>

#include "theme/theme_manager.h"
#include "ui/channel_map_panel.h"
#include "ui/hardware_control_panel.h"
#include "ui/array_preview_panel.h"
#include "ui/channel_analyzer_panel.h"
#include "ui/settings_dialog.h"
#include "ui/top_status_bar.h"

namespace ccv2 {

CommandCenterMainWindow::CommandCenterMainWindow(QWidget *parent)
    : QMainWindow(parent) {
    setWindowTitle(QStringLiteral("Neural Signal Command Center V2"));

    const ConfigMap cfg = m_cfgMgr.load();
    const ConfigSection netCfg = cfg.value(QStringLiteral("Network"));
    const ConfigSection uiCfg = cfg.value(QStringLiteral("UI"));

    const QString host = netCfg.value(QStringLiteral("host"), QStringLiteral("127.0.0.1"));
    const int port = netCfg.value(QStringLiteral("port"), QStringLiteral("10086")).toInt();

    m_networkState = new NetworkState(host, port, this);
    m_channelState = new ChannelAddressState(this);
    m_manualHost = m_networkState->host();
    m_manualPort = m_networkState->port();

    const int savedW = uiCfg.value(QStringLiteral("window_width"), QStringLiteral("1920")).toInt();
    const int savedH = uiCfg.value(QStringLiteral("window_height"), QStringLiteral("1100")).toInt();
    QScreen *screen = QGuiApplication::primaryScreen();
    if (screen) {
        const QRect avail = screen->availableGeometry();
        const int w = qMax(1200, qMin(savedW, avail.width()));
        const int h = qMax(900, qMin(savedH, avail.height()));
        resize(w, h);
    } else {
        resize(qMax(1200, savedW), qMax(900, savedH));
    }

    buildUi();
    applyTheme();

    // Initialize status bar with current state
    m_statusBar->setEndpoint(m_networkState->host(), m_networkState->port());
}

void CommandCenterMainWindow::buildUi() {
    auto *root = new QWidget;
    setCentralWidget(root);
    auto *shell = new QVBoxLayout(root);
    shell->setContentsMargins(0, 0, 0, 0);
    shell->setSpacing(0);

    // Top status bar
    m_statusBar = new TopStatusBar;
    shell->addWidget(m_statusBar);
    connect(m_statusBar, &TopStatusBar::settingsClicked, this, &CommandCenterMainWindow::showSettings);

    // Body: navigation + content
    auto *body = new QHBoxLayout;
    body->setContentsMargins(0, 0, 0, 0);
    body->setSpacing(0);
    shell->addLayout(body, 1);

    // Left navigation
    auto *navWidget = new QWidget;
    navWidget->setObjectName(QStringLiteral("navWidget"));
    auto *navLayout = new QVBoxLayout(navWidget);
    navLayout->setContentsMargins(8, 12, 8, 12);
    navLayout->setSpacing(0);

    auto *navTitle = new QLabel(QStringLiteral("NAVIGATION"));
    navTitle->setObjectName(QStringLiteral("navSectionTitle"));
    navTitle->setStyleSheet(QStringLiteral("color: #64748b; font-size: 10px; font-weight: 700; letter-spacing: 1px; padding: 4px 8px 8px 8px;"));
    navLayout->addWidget(navTitle);

    m_nav = new QListWidget;
    m_nav->setObjectName(QStringLiteral("leftNav"));
    m_nav->addItem(QStringLiteral("  Channel Map"));
    m_nav->addItem(QStringLiteral("  Hardware Control"));
    m_nav->addItem(QStringLiteral("  Array Preview"));
    m_nav->addItem(QStringLiteral("  Channel Analyzer"));
    m_nav->setCurrentRow(0);
    navLayout->addWidget(m_nav, 1);
    body->addWidget(navWidget, 0);

    // Content area
    m_stack = new QStackedWidget;
    body->addWidget(m_stack, 1);

    // Create pages
    m_pageMap = new ChannelMapPanel(m_channelState);
    m_pageHw = new HardwareControlPanel(&m_cfgMgr, m_networkState, m_channelState);
    m_pagePreview = new ArrayPreviewPanel(&m_cfgMgr, m_networkState, m_channelState);
    m_pageAnalyzer = new ChannelAnalyzerPanel(&m_cfgMgr, m_networkState, m_channelState);

    m_stack->addWidget(m_pageMap);
    m_stack->addWidget(m_pageHw);
    m_stack->addWidget(m_pagePreview);
    m_stack->addWidget(m_pageAnalyzer);

    connect(m_nav, &QListWidget::currentRowChanged, m_stack, &QStackedWidget::setCurrentIndex);
}

void CommandCenterMainWindow::showSettings() {
    auto *dlg = new SettingsDialog(
        m_networkState->host(), m_networkState->port(),
        ThemeManager::themeNames().value(0), this);

    connect(dlg, &SettingsDialog::networkApplied, this, [this](const QString &host, int port) {
        setEndpoint(host, port, true, true);
    });

    connect(dlg, &SettingsDialog::localTestToggled, this, [this](bool enabled) {
        if (enabled) {
            m_manualHost = m_networkState->host();
            m_manualPort = m_networkState->port();
            setEndpoint(QStringLiteral("127.0.0.1"), 10086, false, false);
        } else {
            setEndpoint(m_manualHost, m_manualPort, false, true);
        }
    });

    connect(dlg, &SettingsDialog::themeChanged, this, [this](int index) {
        Q_UNUSED(index);
        applyTheme();
    });

    dlg->exec();
    dlg->deleteLater();
}

void CommandCenterMainWindow::applyTheme() {
    const ThemeStyle style = ThemeManager::fromIndex(0);
    setStyleSheet(ThemeManager::styleSheetFor(style));

    const ThemeManager::ColorTokens tokens = ThemeManager::colors();

    // Apply wave palette to realtime plot
    QMap<QString, QString> wavePalette;
    wavePalette.insert(QStringLiteral("bg"), tokens.plotBg);
    wavePalette.insert(QStringLiteral("title"), tokens.textSecondary);
    wavePalette.insert(QStringLiteral("grid"), tokens.cardBorder);
    wavePalette.insert(QStringLiteral("wave"), tokens.waveLine);
    wavePalette.insert(QStringLiteral("axis"), tokens.plotAxis);
    m_pagePreview->setWaveTheme(wavePalette);

    // Apply plot theme to channel analyzer
    m_pageAnalyzer->setPlotTheme(tokens.plotBg, tokens.plotAxis);

    // Apply map theme to channel map
    QMap<QString, QString> mapPalette;
    mapPalette.insert(QStringLiteral("bg"), tokens.plotBg);
    mapPalette.insert(QStringLiteral("electrode"), tokens.inputBg);
    mapPalette.insert(QStringLiteral("outline"), tokens.cardBorder);
    mapPalette.insert(QStringLiteral("selected"), tokens.primaryAccent);
    mapPalette.insert(QStringLiteral("block_deep"), tokens.navSelected);
    mapPalette.insert(QStringLiteral("block_light"), tokens.cardBorder);
    mapPalette.insert(QStringLiteral("block_label_deep"), tokens.textPrimary);
    mapPalette.insert(QStringLiteral("block_label_light"), tokens.textSecondary);
    mapPalette.insert(QStringLiteral("boundary"), tokens.cardBorder);
    m_pageMap->setMapTheme(mapPalette);

    saveUiToConfig();
}

void CommandCenterMainWindow::saveUiToConfig() {
    ConfigMap cfg = m_cfgMgr.load();
    cfg[QStringLiteral("UI")][QStringLiteral("theme")] = ThemeManager::themeNames().value(0);
    const QRect g = isMaximized() ? normalGeometry() : geometry();
    cfg[QStringLiteral("UI")][QStringLiteral("window_width")] = QString::number(qMax(1200, g.width()));
    cfg[QStringLiteral("UI")][QStringLiteral("window_height")] = QString::number(qMax(900, g.height()));
    m_cfgMgr.save(cfg);
}

void CommandCenterMainWindow::saveNetworkToConfig(const QString &host, int port) {
    ConfigMap cfg = m_cfgMgr.load();
    cfg[QStringLiteral("Network")][QStringLiteral("host")] = host;
    cfg[QStringLiteral("Network")][QStringLiteral("port")] = QString::number(port);
    m_cfgMgr.save(cfg);
}

void CommandCenterMainWindow::setEndpoint(const QString &host, int port, bool saveCfg, bool rememberManual) {
    m_networkState->setEndpoint(host, port);
    const QString normalizedHost = m_networkState->host();
    const int normalizedPort = m_networkState->port();
    if (rememberManual) {
        m_manualHost = normalizedHost;
        m_manualPort = normalizedPort;
    }
    if (saveCfg) {
        saveNetworkToConfig(normalizedHost, normalizedPort);
    }
    m_statusBar->setEndpoint(normalizedHost, normalizedPort);
}

void CommandCenterMainWindow::closeEvent(QCloseEvent *event) {
    saveUiToConfig();
    if (m_pagePreview) {
        m_pagePreview->shutdown();
    }
    if (m_pageAnalyzer) {
        m_pageAnalyzer->shutdown();
    }
    event->accept();
}

}  // namespace ccv2
