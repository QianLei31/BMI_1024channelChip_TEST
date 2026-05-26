#include "ui/waveform_widget.h"

#include <QFont>
#include <QFontMetrics>
#include <QPainter>
#include <QPolygonF>

#include <cmath>

namespace ccv2 {

namespace {

QString tickText(double value) {
    if (!std::isfinite(value)) {
        return QStringLiteral("0");
    }

    const double av = std::abs(value);
    if (av >= 1000.0) {
        return QString::number(value, 'f', 0);
    }
    if (av >= 100.0) {
        return QString::number(value, 'f', 1);
    }
    if (av >= 10.0) {
        return QString::number(value, 'f', 2);
    }
    return QString::number(value, 'g', 4);
}

}  // namespace

WaveformWidget::WaveformWidget(const QString &title, QWidget *parent)
    : QWidget(parent), m_title(title) {
    m_palette = {
        {QStringLiteral("bg"), QStringLiteral("#0c1a2e")},
        {QStringLiteral("title"), QStringLiteral("#a0b8d0")},
        {QStringLiteral("grid"), QStringLiteral("#1c3350")},
        {QStringLiteral("wave"), QStringLiteral("#00e5ff")},
        {QStringLiteral("axis"), QStringLiteral("#8faaca")},
    };
    setMinimumHeight(120);
}

void WaveformWidget::setTitle(const QString &title) {
    m_title = title;
    update();
}

void WaveformWidget::setData(const QVector<double> &data) {
    m_data = downsample(data);
    m_series.clear();
    if (!m_data.isEmpty()) {
        PlotSeries s;
        s.data = m_data;
        s.color = QColor(m_palette.value(QStringLiteral("wave"), QStringLiteral("#00e5ff")));
        m_series.push_back(s);
    }
    update();
}

void WaveformWidget::setSeries(const QVector<PlotSeries> &series) {
    m_series.clear();
    m_series.reserve(series.size());
    for (const PlotSeries &seriesItem : series) {
        PlotSeries s;
        s.data = downsample(seriesItem.data);
        s.color = seriesItem.color;
        m_series.push_back(s);
    }
    m_data = (m_series.isEmpty() ? QVector<double>{} : m_series.first().data);
    update();
}

void WaveformWidget::setYRange(double yMin, double yMax) {
    if (yMax <= yMin) {
        return;
    }
    if (qFuzzyCompare(m_yMin, yMin) && qFuzzyCompare(m_yMax, yMax)) {
        return;
    }
    m_yMin = yMin;
    m_yMax = yMax;
    update();
}

void WaveformWidget::setXRange(double xMin, double xMax) {
    if (xMax <= xMin) {
        if (!m_hasXRange) {
            return;
        }
        m_hasXRange = false;
        update();
        return;
    }
    if (m_hasXRange && qFuzzyCompare(m_xMin, xMin) && qFuzzyCompare(m_xMax, xMax)) {
        return;
    }
    m_xMin = xMin;
    m_xMax = xMax;
    m_hasXRange = true;
    update();
}

void WaveformWidget::setAxisLabels(const QString &xLabel, const QString &yLabel) {
    if (m_xLabel == xLabel && m_yLabel == yLabel) {
        return;
    }
    m_xLabel = xLabel;
    m_yLabel = yLabel;
    update();
}

void WaveformWidget::setMaxRenderPoints(int points) {
    m_maxRenderPoints = points <= 0 ? 0 : qMax(64, points);
}

void WaveformWidget::setPaletteColors(const QMap<QString, QString> &palette) {
    for (auto it = palette.cbegin(); it != palette.cend(); ++it) {
        m_palette[it.key()] = it.value();
    }
    update();
}

QVector<double> WaveformWidget::downsample(const QVector<double> &data) const {
    if (m_maxRenderPoints <= 0) {
        return data;
    }
    if (data.size() <= m_maxRenderPoints) {
        return data;
    }

    const int step = qMax(1, (data.size() + m_maxRenderPoints - 1) / m_maxRenderPoints);
    QVector<double> sampled;
    sampled.reserve((data.size() + step - 1) / step + 1);
    for (int i = 0; i < data.size(); i += step) {
        sampled.push_back(data[i]);
    }
    if (!sampled.isEmpty() && sampled.back() != data.back()) {
        sampled.push_back(data.back());
    }
    return sampled;
}

void WaveformWidget::paintEvent(QPaintEvent *event) {
    Q_UNUSED(event);

    QPainter painter(this);
    QFont plotFont(QStringLiteral("Microsoft YaHei UI"));
    plotFont.setPointSize(8);
    painter.setFont(plotFont);
    painter.setRenderHint(QPainter::Antialiasing, false);
    const QRect widgetRect = this->rect();

    painter.fillRect(widgetRect, QColor(m_palette.value(QStringLiteral("bg"), QStringLiteral("#0c1a2e"))));
    const QColor titleColor(m_palette.value(QStringLiteral("title"), QStringLiteral("#a0b8d0")));
    const QColor gridColor(m_palette.value(QStringLiteral("grid"), QStringLiteral("#1c3350")));
    const QColor axisColor(m_palette.value(QStringLiteral("axis"), QStringLiteral("#8faaca")));
    painter.setPen(titleColor);
    painter.drawText(8, 14, m_title);

    const QFontMetrics fm(painter.font());
    const int yMaxText = fm.horizontalAdvance(tickText(m_yMax));
    const int yMinText = fm.horizontalAdvance(tickText(m_yMin));
    const int leftMargin = qMax(54, qMax(yMaxText, yMinText) + 16);
    const QRect plotRect = widgetRect.adjusted(leftMargin, 22, -12, -30);
    if (plotRect.width() < 20 || plotRect.height() < 20) {
        return;
    }

    painter.setPen(QPen(gridColor));
    for (int i = 1; i < 4; ++i) {
        const int y = plotRect.top() + plotRect.height() * i / 4;
        painter.drawLine(plotRect.left(), y, plotRect.right(), y);
    }
    for (int i = 1; i < 4; ++i) {
        const int x = plotRect.left() + plotRect.width() * i / 4;
        painter.drawLine(x, plotRect.top(), x, plotRect.bottom());
    }

    painter.setPen(QPen(axisColor, 1));
    painter.drawLine(plotRect.left(), plotRect.top(), plotRect.left(), plotRect.bottom());
    painter.drawLine(plotRect.left(), plotRect.bottom(), plotRect.right(), plotRect.bottom());

    const double ySpan = qMax(1e-12, m_yMax - m_yMin);
    painter.setPen(axisColor);
    for (int i = 0; i <= 4; ++i) {
        const int y = plotRect.top() + plotRect.height() * i / 4;
        const double value = m_yMax - ySpan * static_cast<double>(i) / 4.0;
        painter.drawLine(plotRect.left() - 4, y, plotRect.left(), y);
        painter.drawText(QRect(2, y - fm.height() / 2, leftMargin - 8, fm.height()),
                         Qt::AlignRight | Qt::AlignVCenter,
                         tickText(value));
    }

    int maxSamples = 0;
    for (const PlotSeries &series : m_series) {
        maxSamples = qMax(maxSamples, series.data.size());
    }
    const double xMin = m_hasXRange ? m_xMin : 0.0;
    const double xMax = m_hasXRange ? m_xMax : static_cast<double>(qMax(1, maxSamples - 1));
    const double xSpan = qMax(1e-12, xMax - xMin);
    for (int i = 0; i <= 4; ++i) {
        const int x = plotRect.left() + plotRect.width() * i / 4;
        const double value = xMin + xSpan * static_cast<double>(i) / 4.0;
        painter.drawLine(x, plotRect.bottom(), x, plotRect.bottom() + 4);
        painter.drawText(QRect(x - 42, plotRect.bottom() + 6, 84, fm.height()),
                         Qt::AlignHCenter | Qt::AlignTop,
                         tickText(value));
    }

    if (!m_xLabel.isEmpty()) {
        painter.drawText(QRect(plotRect.right() - 150, plotRect.top() + 2, 146, fm.height()),
                         Qt::AlignRight | Qt::AlignVCenter,
                         m_xLabel);
    }
    if (!m_yLabel.isEmpty()) {
        painter.drawText(QRect(plotRect.left() + 4, plotRect.top() + 2, 150, fm.height()),
                         Qt::AlignLeft | Qt::AlignVCenter,
                         m_yLabel);
    }

    if (m_series.isEmpty()) {
        return;
    }

    for (const PlotSeries &series : m_series) {
        if (series.data.size() < 2) {
            continue;
        }

        const QColor color = series.color.isValid() ? series.color : QColor(m_palette.value(QStringLiteral("wave"), QStringLiteral("#00e5ff")));
        painter.setPen(QPen(color, 1));

        QPolygonF poly;
        poly.reserve(series.data.size());
        const int n = series.data.size();
        for (int i = 0; i < n; ++i) {
            const qreal x = plotRect.left() + (static_cast<qreal>(i) / (n - 1)) * plotRect.width();
            const double vv = qBound(m_yMin, static_cast<double>(series.data[i]), m_yMax);
            const qreal y = plotRect.bottom() - ((vv - m_yMin) / ySpan) * plotRect.height();
            poly << QPointF(x, y);
        }
        painter.drawPolyline(poly);
    }
}

}  // namespace ccv2
