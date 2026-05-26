#include "theme/theme_manager.h"

namespace ccv2 {

QStringList ThemeManager::themeNames() {
    return {QStringLiteral("Neural Dark")};
}

ThemeStyle ThemeManager::fromIndex(int idx) {
    Q_UNUSED(idx);
    return ThemeStyle::NeuralDark;
}

ThemeManager::ColorTokens ThemeManager::colors() {
    return {
        QStringLiteral("#0a0f1a"),   // appBg
        QStringLiteral("#111827"),   // cardBg
        QStringLiteral("#1e293b"),   // cardBorder
        QStringLiteral("#3b82f6"),   // primaryAccent
        QStringLiteral("#8b5cf6"),   // secondaryAccent
        QStringLiteral("#22c55e"),   // success
        QStringLiteral("#f59e0b"),   // warning
        QStringLiteral("#ef4444"),   // error
        QStringLiteral("#e2e8f0"),   // textPrimary
        QStringLiteral("#94a3b8"),   // textSecondary
        QStringLiteral("#0f172a"),   // navBg
        QStringLiteral("#1e3a5f"),   // navSelected
        QStringLiteral("#0c1222"),   // inputBg
        QStringLiteral("#080d19"),   // plotBg
        QStringLiteral("#475569"),   // plotAxis
        QStringLiteral("#38bdf8"),   // waveLine
        QStringLiteral("#0b1120"),   // statusBarBg
    };
}

QString ThemeManager::styleSheetFor(ThemeStyle style) {
    Q_UNUSED(style);

    const ColorTokens c = colors();

    return QStringLiteral(R"(
        /* === Base === */
        QWidget {
            color: %1;
            font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
            font-size: 13px;
            background: transparent;
        }

        QMainWindow {
            background: %2;
        }

        /* === Status Bar === */
        QWidget#topStatusBar {
            background: %17;
            border-bottom: 1px solid %3;
        }
        QLabel#statusTitle {
            font-size: 15px;
            font-weight: 700;
            color: %1;
            letter-spacing: 0.5px;
        }
        QLabel#statusEndpoint, QWidget#topStatusBar QLabel {
            color: %9;
            font-size: 12px;
        }
        QFrame#statusSeparator {
            background: %3;
            max-width: 1px;
            margin: 6px 2px;
        }
        QPushButton#btnSettings {
            background: transparent;
            color: %9;
            border: 1px solid %3;
            border-radius: 6px;
            padding: 4px 12px;
            font-size: 12px;
        }
        QPushButton#btnSettings:hover {
            border-color: %4;
            color: %4;
        }

        /* === Status Badges === */
        QLabel#badgeOk {
            color: %6;
            font-weight: 600;
            font-size: 12px;
            padding: 1px 6px;
            background: rgba(34,197,94,0.1);
            border-radius: 4px;
        }
        QLabel#badgeWarn {
            color: %7;
            font-weight: 600;
            font-size: 12px;
            padding: 1px 6px;
            background: rgba(245,158,11,0.1);
            border-radius: 4px;
        }
        QLabel#badgeError {
            color: %8;
            font-weight: 600;
            font-size: 12px;
            padding: 1px 6px;
            background: rgba(239,68,68,0.1);
            border-radius: 4px;
        }
        QLabel#badgeDisconnected {
            color: %8;
            font-weight: 600;
            font-size: 12px;
            padding: 1px 6px;
            background: rgba(239,68,68,0.1);
            border-radius: 4px;
        }
        QLabel#badgeIdle {
            color: %9;
            font-size: 12px;
            padding: 1px 6px;
        }

        /* === Left Navigation === */
        QListWidget#leftNav {
            background: %10;
            border: 1px solid %3;
            border-radius: 10px;
            padding: 6px;
            min-width: 200px;
            max-width: 240px;
            outline: 0px;
        }
        QListWidget#leftNav::item {
            border-radius: 8px;
            padding: 14px 12px;
            margin: 3px 4px;
            background: transparent;
            color: %9;
            font-size: 13px;
        }
        QListWidget#leftNav::item:selected {
            background: %11;
            color: %1;
            font-weight: 600;
            border-left: 3px solid %4;
        }
        QListWidget#leftNav::item:hover:!selected {
            background: rgba(59,130,246,0.08);
        }

        /* === Card / Group Box === */
        QGroupBox {
            background: %3;
            border: 1px solid %3;
            border-radius: 12px;
            margin-top: 16px;
            font-weight: 600;
            color: %1;
            padding: 16px 14px 12px 14px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 14px;
            padding: 0 8px;
            color: %9;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        /* === Inputs === */
        QLineEdit, QComboBox, QPlainTextEdit, QSpinBox, QDoubleSpinBox {
            background: %12;
            color: %1;
            border: 1px solid %3;
            border-radius: 8px;
            padding: 6px 10px;
            selection-background-color: %4;
        }
        QLineEdit:focus, QComboBox:focus, QPlainTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
            border-color: %4;
        }
        QComboBox::drop-down {
            border: none;
            width: 24px;
        }
        QComboBox QAbstractItemView {
            background: %3;
            color: %1;
            border: 1px solid %3;
            selection-background-color: %4;
        }

        /* === Primary Button === */
        QPushButton {
            background: %4;
            color: #ffffff;
            border: 1px solid %4;
            border-radius: 8px;
            padding: 7px 16px;
            font-weight: 600;
            font-size: 13px;
        }
        QPushButton:hover {
            background: #2563eb;
            border-color: #60a5fa;
        }
        QPushButton:pressed {
            background: #1d4ed8;
        }
        QPushButton:disabled {
            background: %3;
            color: %9;
            border-color: %3;
        }

        /* === Danger Button === */
        QPushButton[buttonRole="danger"], QPushButton#btnDanger {
            background: %8;
            border-color: %8;
        }
        QPushButton[buttonRole="danger"]:hover, QPushButton#btnDanger:hover {
            background: #dc2626;
            border-color: #f87171;
        }

        /* === Ghost Button === */
        QPushButton[buttonRole="ghost"], QPushButton#btnGhost {
            background: transparent;
            color: %9;
            border: 1px solid %3;
        }
        QPushButton[buttonRole="ghost"]:hover, QPushButton#btnGhost:hover {
            border-color: %4;
            color: %4;
        }

        /* === Checkbox === */
        QCheckBox {
            color: %1;
            spacing: 8px;
        }
        QCheckBox::indicator {
            width: 16px;
            height: 16px;
            border-radius: 4px;
            border: 1px solid %3;
            background: %12;
        }
        QCheckBox::indicator:checked {
            background: %4;
            border-color: %4;
        }

        /* === Table / List === */
        QTableWidget, QTableView {
            background: %12;
            alternate-background-color: %3;
            border: 1px solid %3;
            border-radius: 8px;
            gridline-color: %3;
            color: %1;
        }
        QTableWidget::item:selected, QTableView::item:selected {
            background: %11;
            color: #ffffff;
        }
        QHeaderView::section {
            background: %3;
            color: %9;
            border: none;
            border-bottom: 1px solid %3;
            padding: 6px 8px;
            font-weight: 600;
            font-size: 11px;
            text-transform: uppercase;
        }

        /* === Scroll Bar === */
        QScrollBar:vertical {
            background: transparent;
            width: 8px;
            margin: 0;
        }
        QScrollBar::handle:vertical {
            background: %3;
            border-radius: 4px;
            min-height: 32px;
        }
        QScrollBar::handle:vertical:hover {
            background: %4;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0;
        }
        QScrollBar:horizontal {
            background: transparent;
            height: 8px;
            margin: 0;
        }
        QScrollBar::handle:horizontal {
            background: %3;
            border-radius: 4px;
            min-width: 32px;
        }
        QScrollBar::handle:horizontal:hover {
            background: %4;
        }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            width: 0;
        }

        /* === Slider === */
        QSlider::groove:horizontal {
            height: 4px;
            background: %3;
            border-radius: 2px;
        }
        QSlider::handle:horizontal {
            background: %4;
            width: 14px;
            height: 14px;
            margin: -5px 0;
            border-radius: 7px;
        }
        QSlider::sub-page:horizontal {
            background: %4;
            border-radius: 2px;
        }

        /* === Label Styles === */
        QLabel#title {
            font-size: 24px;
            font-weight: 800;
            color: %1;
            letter-spacing: 0.5px;
        }
        QLabel#subtitle {
            color: %9;
            font-size: 13px;
            margin-bottom: 4px;
        }

        /* === Page Header === */
        QLabel#pageTitle {
            font-size: 20px;
            font-weight: 700;
            color: %1;
        }
        QLabel#pageSubtitle {
            font-size: 12px;
            color: %9;
            margin-top: 2px;
        }

        /* === Dialog === */
        QDialog {
            background: %2;
            border: 1px solid %3;
            border-radius: 12px;
        }

        /* === ToolTip === */
        QToolTip {
            background: %3;
            color: %1;
            border: 1px solid %3;
            border-radius: 6px;
            padding: 4px 8px;
            font-size: 12px;
        }

        /* === Scroll Area === */
        QScrollArea {
            border: none;
            background: transparent;
        }

        /* === Frame (networkCard) === */
        QFrame#networkCard {
            background: %12;
            border: 1px solid %3;
            border-radius: 8px;
            padding: 8px;
        }

        /* === Splitter === */
        QSplitter::handle {
            background: %3;
            width: 2px;
        }
        QSplitter::handle:hover {
            background: %4;
        }
    )")
        .arg(c.textPrimary)      // %1
        .arg(c.appBg)            // %2
        .arg(c.cardBorder)       // %3
        .arg(c.primaryAccent)    // %4
        .arg(c.secondaryAccent)  // %5
        .arg(c.success)          // %6
        .arg(c.warning)          // %7
        .arg(c.error)            // %8
        .arg(c.textSecondary)    // %9
        .arg(c.navBg)            // %10
        .arg(c.navSelected)      // %11
        .arg(c.inputBg)          // %12
        .arg(c.plotBg)           // %13
        .arg(c.plotAxis)         // %14
        .arg(c.waveLine)         // %15
        .arg(c.cardBg)           // %16
        .arg(c.statusBarBg);     // %17
}

}  // namespace ccv2
