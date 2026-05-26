#pragma once

#include <QCheckBox>
#include <QLabel>
#include <QLineEdit>
#include <QListWidget>
#include <QMap>
#include <QPlainTextEdit>
#include <QPushButton>
#include <QSet>
#include <QSlider>
#include <QVector>
#include <QWidget>
#include <QVariantMap>

#include "core/channel_address_state.h"

namespace ccv2 {

class ElectrodeMapView;

class ChannelMapPanel : public QWidget {
    Q_OBJECT

public:
    explicit ChannelMapPanel(ChannelAddressState *channelState, QWidget *parent = nullptr);
    void setMapTheme(const QMap<QString, QString> &palette);

private slots:
    void onZoomChanged(int zoomPercent);
    void onBatchModifySelect();
    void onBatchModifyUnselect();
    void onSelectAll();
    void onApplyGlobalChannels();
    void onRefreshOutput();
    void onCopyOutput();
    void syncUiFromState();

private:
    QSet<int> parseIntRanges(const QString &text, int minimum, int maximum, bool *ok, QString *error) const;
    void onMapPairsChanged(const QSet<QPair<int, int>> &pairs);
    void onElectrodeClicked(const QVariantMap &info);
    void batchModify(bool makeSelected);

    ChannelAddressState *m_channelState;
    ElectrodeMapView *m_mapView{nullptr};

    QLineEdit *m_blockRangeEdit{nullptr};
    QVector<QCheckBox *> m_localChecks;
    QLineEdit *m_globalEdit{nullptr};
    QLabel *m_zoomLabel{nullptr};
    QSlider *m_zoomSlider{nullptr};

    QLabel *m_blockLabel{nullptr};
    QLabel *m_localLabel{nullptr};
    QLabel *m_globalLabel{nullptr};
    QLabel *m_electrodeLabel{nullptr};
    QLabel *m_spiBitsLabel{nullptr};
    QListWidget *m_historyList{nullptr};

    QLabel *m_selCountLabel{nullptr};
    QPlainTextEdit *m_outputEdit{nullptr};
};

}  // namespace ccv2
