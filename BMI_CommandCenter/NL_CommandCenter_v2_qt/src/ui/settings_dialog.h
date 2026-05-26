#pragma once

#include <QCheckBox>
#include <QComboBox>
#include <QDialog>
#include <QLineEdit>
#include <QPushButton>
#include <QSpinBox>

namespace ccv2 {

class SettingsDialog : public QDialog {
    Q_OBJECT

public:
    explicit SettingsDialog(const QString &host, int port, const QString &theme, QWidget *parent = nullptr);

    QString host() const;
    int port() const;
    bool localTestMode() const;

signals:
    void networkApplied(const QString &host, int port);
    void themeChanged(int index);
    void localTestToggled(bool enabled);

private:
    QLineEdit *m_hostEdit{nullptr};
    QSpinBox *m_portSpin{nullptr};
    QCheckBox *m_localTestCheck{nullptr};
    QComboBox *m_themeCombo{nullptr};
    QPushButton *m_applyBtn{nullptr};
    QPushButton *m_cancelBtn{nullptr};
};

}  // namespace ccv2
