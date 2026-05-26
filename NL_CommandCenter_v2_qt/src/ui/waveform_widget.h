#pragma once

#include <QColor>
#include <QMap>
#include <QString>
#include <QVector>
#include <QWidget>

namespace ccv2 {

class WaveformWidget : public QWidget {
    Q_OBJECT

public:
    struct PlotSeries {
        QVector<double> data;
        QColor color;
    };

    explicit WaveformWidget(const QString &title = QString(), QWidget *parent = nullptr);

    void setTitle(const QString &title);
    void setData(const QVector<double> &data);
    void setSeries(const QVector<PlotSeries> &series);
    void setYRange(double yMin, double yMax);
    void setXRange(double xMin, double xMax);
    void setAxisLabels(const QString &xLabel, const QString &yLabel);
    void setMaxRenderPoints(int points);
    void setPaletteColors(const QMap<QString, QString> &palette);

protected:
    void paintEvent(QPaintEvent *event) override;

private:
    QVector<double> downsample(const QVector<double> &data) const;

    QString m_title;
    QString m_xLabel{QStringLiteral("Sample")};
    QString m_yLabel{QStringLiteral("Value")};
    QVector<double> m_data;
    QVector<PlotSeries> m_series;
    double m_yMin{0.0};
    double m_yMax{1.8};
    double m_xMin{0.0};
    double m_xMax{1.0};
    bool m_hasXRange{false};
    int m_maxRenderPoints{1600};
    QMap<QString, QString> m_palette;
};

}  // namespace ccv2
