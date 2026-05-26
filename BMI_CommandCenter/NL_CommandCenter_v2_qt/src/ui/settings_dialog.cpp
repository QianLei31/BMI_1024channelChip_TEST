#include "ui/settings_dialog.h"

#include <QDialogButtonBox>
#include <QFormLayout>
#include <QGroupBox>
#include <QLabel>
#include <QVBoxLayout>

#include "theme/theme_manager.h"

namespace ccv2 {

SettingsDialog::SettingsDialog(const QString &host, int port, const QString &theme, QWidget *parent)
    : QDialog(parent) {
    setWindowTitle(QStringLiteral("Settings"));
    setMinimumWidth(420);
    setObjectName(QStringLiteral("settingsDialog"));

    auto *root = new QVBoxLayout(this);
    root->setSpacing(12);

    auto *netGroup = new QGroupBox(QStringLiteral("Network Configuration"));
    auto *netForm = new QFormLayout(netGroup);
    netForm->setSpacing(8);

    m_hostEdit = new QLineEdit(host);
    m_hostEdit->setPlaceholderText(QStringLiteral("192.168.2.10"));
    netForm->addRow(QStringLiteral("Host"), m_hostEdit);

    m_portSpin = new QSpinBox;
    m_portSpin->setRange(1, 65535);
    m_portSpin->setValue(port);
    netForm->addRow(QStringLiteral("Port"), m_portSpin);

    m_localTestCheck = new QCheckBox(QStringLiteral("Local Test Mode"));
    netForm->addRow(m_localTestCheck);

    root->addWidget(netGroup);

    auto *uiGroup = new QGroupBox(QStringLiteral("Appearance"));
    auto *uiForm = new QFormLayout(uiGroup);
    uiForm->setSpacing(8);

    m_themeCombo = new QComboBox;
    m_themeCombo->addItems(ThemeManager::themeNames());
    const QStringList names = ThemeManager::themeNames();
    const int idx = names.indexOf(theme);
    m_themeCombo->setCurrentIndex(idx >= 0 ? idx : 0);
    uiForm->addRow(QStringLiteral("Theme"), m_themeCombo);

    root->addWidget(uiGroup);

    auto *buttonBox = new QDialogButtonBox(QDialogButtonBox::Apply | QDialogButtonBox::Cancel);
    buttonBox->button(QDialogButtonBox::Apply)->setText(QStringLiteral("Apply"));
    buttonBox->button(QDialogButtonBox::Cancel)->setText(QStringLiteral("Close"));
    root->addWidget(buttonBox);

    connect(buttonBox, &QDialogButtonBox::accepted, this, [this]() {
        emit networkApplied(m_hostEdit->text().trimmed(), m_portSpin->value());
    });
    connect(buttonBox, &QDialogButtonBox::rejected, this, &QDialog::reject);

    connect(m_localTestCheck, &QCheckBox::toggled, this, [this](bool enabled) {
        m_hostEdit->setEnabled(!enabled);
        m_portSpin->setEnabled(!enabled);
        emit localTestToggled(enabled);
    });

    connect(m_themeCombo, QOverload<int>::of(&QComboBox::currentIndexChanged),
            this, &SettingsDialog::themeChanged);
}

QString SettingsDialog::host() const { return m_hostEdit->text().trimmed(); }
int SettingsDialog::port() const { return m_portSpin->value(); }
bool SettingsDialog::localTestMode() const { return m_localTestCheck->isChecked(); }

}  // namespace ccv2
