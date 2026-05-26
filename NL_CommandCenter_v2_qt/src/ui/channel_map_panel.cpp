#include "ui/channel_map_panel.h"

#include <algorithm>
#include <functional>

#include <QApplication>
#include <QClipboard>
#include <QFormLayout>
#include <QGraphicsRectItem>
#include <QGraphicsScene>
#include <QGraphicsSceneMouseEvent>
#include <QGraphicsTextItem>
#include <QGraphicsView>
#include <QGridLayout>
#include <QGroupBox>
#include <QHBoxLayout>
#include <QMessageBox>
#include <QPainter>
#include <QPainterPath>
#include <QResizeEvent>
#include <QSplitter>
#include <QStyleOptionGraphicsItem>
#include <QVBoxLayout>
#include <QWheelEvent>

namespace ccv2 {

namespace {

QString blendHex(const QString &colorA, const QString &colorB, double ratio) {
    const double r = qBound(0.0, ratio, 1.0);
    QColor a(colorA);
    QColor b(colorB);
    if (!a.isValid()) {
        a = QColor(QStringLiteral("#4d4d4d"));
    }
    if (!b.isValid()) {
        b = QColor(QStringLiteral("#b0b0b0"));
    }

    const int rr = static_cast<int>(a.red() * (1.0 - r) + b.red() * r);
    const int gg = static_cast<int>(a.green() * (1.0 - r) + b.green() * r);
    const int bb = static_cast<int>(a.blue() * (1.0 - r) + b.blue() * r);
    return QColor(rr, gg, bb).name();
}

struct ElectrodeInfo {
    double x{0.0};
    double y{0.0};
    int pCol{0};
    int pRow{0};
    int block{0};
    int blockInCol{0};
    int idInBlock{0};
    int electrodeGlobal{0};
    int localChannel{0};
    int globalChannel{0};
};

class ElectrodeRectItem : public QGraphicsRectItem {
public:
    ElectrodeRectItem(const QRectF &rect, int idx, const std::function<void(int)> &clickCallback, QGraphicsItem *parent = nullptr)
        : QGraphicsRectItem(rect, parent), m_idx(idx), m_clickCallback(clickCallback) {}

protected:
    void paint(QPainter *painter, const QStyleOptionGraphicsItem *option, QWidget *widget) override {
        Q_UNUSED(option);
        Q_UNUSED(widget);

        painter->setRenderHint(QPainter::Antialiasing, true);
        painter->setPen(pen());
        painter->setBrush(brush());
        painter->drawRoundedRect(rect(), 2.2, 2.2);

        const QRectF inner = rect().adjusted(2.2, 2.2, -2.2, -2.2);
        if (inner.width() > 0.0 && inner.height() > 0.0) {
            QColor innerColor = isSelected() ? QColor(QStringLiteral("#fff3cf")) : QColor(QStringLiteral("#f6fbff"));
            innerColor.setAlpha(220);
            painter->setPen(Qt::NoPen);
            painter->setBrush(innerColor);
            painter->drawRoundedRect(inner, 1.8, 1.8);
        }
    }

    void mousePressEvent(QGraphicsSceneMouseEvent *event) override {
        QGraphicsRectItem::mousePressEvent(event);
        if (m_clickCallback) {
            m_clickCallback(m_idx);
        }
    }

private:
    int m_idx{0};
    std::function<void(int)> m_clickCallback;
};

}  // namespace

class ElectrodeMapView : public QGraphicsView {
public:
    explicit ElectrodeMapView(QWidget *parent = nullptr)
        : QGraphicsView(parent) {
        setScene(new QGraphicsScene(this));
        setBackgroundBrush(QBrush(QColor(m_bgColor)));
        setRenderHint(QPainter::Antialiasing, true);
        setDragMode(QGraphicsView::RubberBandDrag);
        setRubberBandSelectionMode(Qt::IntersectsItemShape);
        setTransformationAnchor(QGraphicsView::AnchorViewCenter);
        setResizeAnchor(QGraphicsView::AnchorViewCenter);
        setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOn);
        setVerticalScrollBarPolicy(Qt::ScrollBarAlwaysOn);

        generateLayoutDataStrict();
        computeColumnPositions();

        connect(scene(), &QGraphicsScene::selectionChanged, this, [this]() { onSceneSelectionChanged(); });
        rebuildScene(false);
        fitToChip();
    }

    void setOnPairSelectionChanged(const std::function<void(const QSet<QPair<int, int>> &)> &cb) { m_pairSelectionChanged = cb; }
    void setOnElectrodeClicked(const std::function<void(const QVariantMap &)> &cb) { m_electrodeClicked = cb; }
    void setOnZoomChanged(const std::function<void(int)> &cb) { m_zoomChanged = cb; }

    void fitToChip() {
        const QRectF bbox = scene()->itemsBoundingRect();
        if (bbox.isNull()) {
            return;
        }
        resetTransform();
        fitInView(bbox.adjusted(-12, -12, 12, 12), m_fitMode);
        m_zoomPercent = 100;
        m_autoFit = true;
        if (m_zoomChanged) {
            m_zoomChanged(m_zoomPercent);
        }
    }

    void setZoomPercent(int percent) {
        const int p = qBound(20, percent, 500);
        if (p == 100) {
            fitToChip();
            return;
        }

        const QRectF bbox = scene()->itemsBoundingRect();
        if (bbox.isNull()) {
            return;
        }

        resetTransform();
        fitInView(bbox.adjusted(-12, -12, 12, 12), m_fitMode);
        const double factor = static_cast<double>(p) / 100.0;
        scale(factor, factor);

        m_zoomPercent = p;
        m_autoFit = false;
        if (m_zoomChanged) {
            m_zoomChanged(m_zoomPercent);
        }
    }

    void zoomIn() { setZoomPercent(m_zoomPercent + 10); }
    void zoomOut() { setZoomPercent(m_zoomPercent - 10); }

    void setSelectedPairs(const QSet<QPair<int, int>> &pairs) {
        m_syncing = true;
        for (auto it = m_itemsByIdx.cbegin(); it != m_itemsByIdx.cend(); ++it) {
            it.value()->setSelected(false);
        }

        for (auto it = pairs.cbegin(); it != pairs.cend(); ++it) {
            const QVector<ElectrodeRectItem *> items = m_pairToItems.value(*it);
            for (ElectrodeRectItem *item : items) {
                item->setSelected(true);
            }
        }

        m_syncing = false;
        refreshItemStyles();
    }

    void setThemePalette(const QMap<QString, QString> &palette) {
        bool changed = false;
        auto updateColor = [&](const QString &key, QString &dst) {
            const QString value = palette.value(key).trimmed();
            if (!value.isEmpty()) {
                dst = value;
                changed = true;
            }
        };

        updateColor(QStringLiteral("bg"), m_bgColor);
        updateColor(QStringLiteral("electrode"), m_electrodeColor);
        updateColor(QStringLiteral("outline"), m_electrodeOutline);
        updateColor(QStringLiteral("selected"), m_selectedColor);
        updateColor(QStringLiteral("block_deep"), m_blockColorDeep);
        updateColor(QStringLiteral("block_light"), m_blockColorLight);
        updateColor(QStringLiteral("block_label_deep"), m_blockLabelTextDeep);
        updateColor(QStringLiteral("block_label_light"), m_blockLabelTextLight);
        updateColor(QStringLiteral("boundary"), m_chipBoundaryColor);

        if (!changed) {
            return;
        }

        rebuildScene(true);
        if (m_autoFit) {
            fitToChip();
        } else {
            setZoomPercent(m_zoomPercent);
        }
    }

protected:
    void resizeEvent(QResizeEvent *event) override {
        QGraphicsView::resizeEvent(event);
        if (m_autoFit) {
            fitToChip();
        }
    }

    void wheelEvent(QWheelEvent *event) override {
        if (event->modifiers() & Qt::ControlModifier) {
            if (event->angleDelta().y() > 0) {
                zoomIn();
            } else {
                zoomOut();
            }
            event->accept();
            return;
        }
        QGraphicsView::wheelEvent(event);
    }

private:
    static constexpr int kPadSize = 18;
    static constexpr int kYSpacing = 20;
    static constexpr int kSmallXSpacing = 50;
    static constexpr int kLargeXSpacing = 118;
    static constexpr int kChipBoundaryPadding = 96;
    static constexpr int kNumPhysicalCols = 16;
    static constexpr int kNumBlocksPerCol = 4;
    static constexpr int kNumElectrodesPerBlock = 16;

    QString m_bgColor{QStringLiteral("#f4fbff")};
    QString m_electrodeColor{QStringLiteral("#d9eaf4")};
    QString m_electrodeOutline{QStringLiteral("#000508")};
    QString m_selectedColor{QStringLiteral("#ff6b35")};
    QString m_blockColorDeep{QStringLiteral("#1C6CA1")};
    QString m_blockColorLight{QStringLiteral("#98c1d9")};
    QString m_blockLabelTextDeep{QStringLiteral("#ffffff")};
    QString m_blockLabelTextLight{QStringLiteral("#072039")};
    QString m_chipBoundaryColor{QStringLiteral("#072039")};

    QVector<ElectrodeInfo> m_electrodesData;
    QMap<int, double> m_colX;
    QMap<int, double> m_colHalfWidth;
    QMap<int, ElectrodeRectItem *> m_itemsByIdx;
    QMap<QPair<int, int>, QVector<ElectrodeRectItem *>> m_pairToItems;

    bool m_syncing{false};
    int m_zoomPercent{100};
    bool m_autoFit{true};
    Qt::AspectRatioMode m_fitMode{Qt::KeepAspectRatio};

    std::function<void(const QSet<QPair<int, int>> &)> m_pairSelectionChanged;
    std::function<void(const QVariantMap &)> m_electrodeClicked;
    std::function<void(int)> m_zoomChanged;

    QSet<QPair<int, int>> selectedPairsFromScene() const {
        QSet<QPair<int, int>> selectedPairs;
        const QList<QGraphicsItem *> items = scene()->selectedItems();
        for (QGraphicsItem *item : items) {
            const QVariant idxVar = item->data(0);
            if (!idxVar.isValid()) {
                continue;
            }
            const int idx = idxVar.toInt();
            if (idx < 0 || idx >= m_electrodesData.size()) {
                continue;
            }
            const ElectrodeInfo &info = m_electrodesData[idx];
            selectedPairs.insert({info.block, info.localChannel});
        }
        return selectedPairs;
    }

    void rebuildScene(bool keepSelection) {
        const QSet<QPair<int, int>> selectedPairs = keepSelection ? selectedPairsFromScene() : QSet<QPair<int, int>>{};

        m_syncing = true;
        scene()->clear();
        m_itemsByIdx.clear();
        m_pairToItems.clear();
        setBackgroundBrush(QBrush(QColor(m_bgColor)));
        drawChipBoundary();
        drawBlockBackgroundsAndLabels();
        drawElectrodes();
        m_syncing = false;

        if (!selectedPairs.isEmpty()) {
            setSelectedPairs(selectedPairs);
        }
    }

    void generateLayoutDataStrict() {
        m_electrodesData.clear();
        const double startX = 60.0;
        const double startY = 60.0;
        double currentX = startX;

        for (int pCol = 0; pCol < kNumPhysicalCols; ++pCol) {
            for (int blockInCol = 0; blockInCol < kNumBlocksPerCol; ++blockInCol) {
                for (int idInBlock = 0; idInBlock < kNumElectrodesPerBlock; ++idInBlock) {
                    const int pRow = blockInCol * kNumElectrodesPerBlock + idInBlock;
                    const double y = startY + pRow * kYSpacing;

                    const int base = pCol * kNumBlocksPerCol;
                    const int blockNum = (pCol % 2 == 0) ? (base + blockInCol) : (base + (kNumBlocksPerCol - 1 - blockInCol));

                    ElectrodeInfo info;
                    info.x = currentX;
                    info.y = y;
                    info.pCol = pCol;
                    info.pRow = pRow;
                    info.block = blockNum;
                    info.blockInCol = blockInCol;
                    info.idInBlock = idInBlock;
                    info.electrodeGlobal = blockNum * kNumElectrodesPerBlock + idInBlock;
                    info.localChannel = idInBlock / 4;
                    info.globalChannel = blockNum * 4 + info.localChannel;
                    m_electrodesData.push_back(info);
                }
            }

            currentX += (pCol % 2 == 0) ? kLargeXSpacing : kSmallXSpacing;
        }
    }

    void computeColumnPositions() {
        m_colX.clear();
        m_colHalfWidth.clear();

        for (const ElectrodeInfo &e : m_electrodesData) {
            if (!m_colX.contains(e.pCol)) {
                m_colX.insert(e.pCol, e.x);
            }
        }

        for (int p = 0; p < kNumPhysicalCols; ++p) {
            const double x = m_colX.value(p);
            QVector<double> candidates;
            if (m_colX.contains(p - 1)) {
                candidates.push_back((x - m_colX.value(p - 1)) / 2.0);
            }
            if (m_colX.contains(p + 1)) {
                candidates.push_back((m_colX.value(p + 1) - x) / 2.0);
            }

            double half = candidates.isEmpty() ? std::max(kPadSize * 4.0, 26.0)
                                               : *std::min_element(candidates.cbegin(), candidates.cend());
            half = std::max(half * 0.95, kPadSize * 2.2);
            m_colHalfWidth.insert(p, half);
        }
    }

    void drawChipBoundary() {
        if (m_electrodesData.isEmpty()) {
            return;
        }

        double minX = m_electrodesData.first().x;
        double maxX = m_electrodesData.first().x;
        double minY = m_electrodesData.first().y;
        double maxY = m_electrodesData.first().y;

        for (const ElectrodeInfo &e : m_electrodesData) {
            minX = std::min(minX, e.x);
            maxX = std::max(maxX, e.x);
            minY = std::min(minY, e.y);
            maxY = std::max(maxY, e.y);
        }

        const QRectF chipRect(minX - kChipBoundaryPadding,
                              minY - kChipBoundaryPadding,
                              (maxX - minX) + 2.0 * kChipBoundaryPadding,
                              (maxY - minY) + 2.0 * kChipBoundaryPadding);

        QColor boardBg(m_blockColorLight);
        boardBg.setAlpha(28);
        QPen boardPen{QColor(m_chipBoundaryColor)};
        boardPen.setWidthF(1.2);
        boardPen.setStyle(Qt::SolidLine);

        QPainterPath boardPath;
        boardPath.addRoundedRect(chipRect, 14.0, 14.0);
        QGraphicsPathItem *boardItem = scene()->addPath(boardPath, boardPen, QBrush(boardBg));
        boardItem->setZValue(-12.0);

        QPen innerPen(QColor(blendHex(m_chipBoundaryColor, m_blockLabelTextDeep, 0.35)));
        innerPen.setWidthF(0.8);
        innerPen.setStyle(Qt::DashLine);
        QGraphicsPathItem *innerItem = scene()->addPath(boardPath, innerPen, QBrush(Qt::NoBrush));
        innerItem->setZValue(-11.0);

        scene()->setSceneRect(chipRect.adjusted(-32.0, -32.0, 32.0, 32.0));
    }

    void drawBlockBackgroundsAndLabels() {
        struct BlockMeta {
            QVector<double> ys;
            int pCol{0};
            int blockInCol{0};
        };

        QMap<int, BlockMeta> blocks;
        for (const ElectrodeInfo &e : m_electrodesData) {
            BlockMeta &meta = blocks[e.block];
            meta.ys.push_back(e.y);
            meta.pCol = e.pCol;
            meta.blockInCol = e.blockInCol;
        }

        for (auto it = blocks.cbegin(); it != blocks.cend(); ++it) {
            const int blockNum = it.key();
            const BlockMeta meta = it.value();

            const double minY = *std::min_element(meta.ys.cbegin(), meta.ys.cend());
            const double maxY = *std::max_element(meta.ys.cbegin(), meta.ys.cend());
            const double cx = m_colX.value(meta.pCol);
            const double halfW = m_colHalfWidth.value(meta.pCol, std::max(kPadSize * 3.0, 22.0));

            const double x0 = cx - halfW;
            const double x1 = cx + halfW;
            const double y0 = minY - kPadSize;
            const double y1 = maxY + kPadSize;

            const bool deep = (meta.blockInCol % 2 == 0);
            QColor bgColor(deep ? m_blockColorDeep : m_blockColorLight);
            QColor textColor(deep ? m_blockLabelTextDeep : m_blockLabelTextLight);
            bgColor.setAlpha(deep ? 190 : 155);

            QPen stroke(QColor(blendHex(bgColor.name(), m_electrodeOutline, 0.45)));
            stroke.setWidthF(0.5);

            QPainterPath blockPath;
            blockPath.addRoundedRect(QRectF(x0, y0, x1 - x0, y1 - y0), 5.0, 5.0);
            QGraphicsPathItem *rectItem = scene()->addPath(blockPath, stroke, QBrush(bgColor));
            rectItem->setZValue(-5.0);

            QGraphicsTextItem *textItem = scene()->addText(QStringLiteral("B%1").arg(blockNum, 2, 10, QLatin1Char('0')));
            textItem->setDefaultTextColor(textColor);
            QFont font = textItem->font();
            font.setPointSize(7);
            font.setBold(true);
            textItem->setFont(font);

            const QRectF tr = textItem->boundingRect();
            textItem->setPos(cx - tr.width() / 2.0, y0 + 4.0);
            textItem->setZValue(-4.0);
        }
    }

    void drawElectrodes() {
        m_itemsByIdx.clear();
        m_pairToItems.clear();

        const double half = static_cast<double>(kPadSize) / 2.0;
        for (int idx = 0; idx < m_electrodesData.size(); ++idx) {
            const ElectrodeInfo &e = m_electrodesData[idx];
            const QRectF rect(e.x - half, e.y - half, kPadSize, kPadSize);

            auto *item = new ElectrodeRectItem(rect, idx, [this](int i) { onItemClicked(i); });
            item->setFlag(QGraphicsItem::ItemIsSelectable, true);
            item->setBrush(QBrush(QColor(m_electrodeColor)));
            item->setPen(QPen(QColor(m_electrodeOutline), 1.1));
            item->setData(0, idx);
            item->setToolTip(
                QStringLiteral("Block=%1, Local=%2, Global=%3, Electrode=%4")
                    .arg(e.block, 2, 10, QLatin1Char('0'))
                    .arg(QString::number(e.localChannel, 2).rightJustified(2, QLatin1Char('0')))
                    .arg(e.globalChannel, 3, 10, QLatin1Char('0'))
                    .arg(e.electrodeGlobal));
            scene()->addItem(item);

            m_itemsByIdx.insert(idx, item);
            m_pairToItems[{e.block, e.localChannel}].push_back(item);
        }
    }

    void onItemClicked(int idx) {
        if (idx < 0 || idx >= m_electrodesData.size()) {
            return;
        }
        const ElectrodeInfo &e = m_electrodesData[idx];
        const QString localBits = QString::number(e.localChannel, 2).rightJustified(2, QLatin1Char('0'));

        QVariantMap info;
        info.insert(QStringLiteral("block"), e.block);
        info.insert(QStringLiteral("local_channel"), e.localChannel);
        info.insert(QStringLiteral("global_channel"), e.globalChannel);
        info.insert(QStringLiteral("electrode_global"), e.electrodeGlobal);
        info.insert(QStringLiteral("local_bits"), localBits);
        info.insert(QStringLiteral("address_bits"), QString::number(e.block, 2).rightJustified(8, QLatin1Char('0')) + localBits);

        if (m_electrodeClicked) {
            m_electrodeClicked(info);
        }
    }

    void refreshItemStyles() {
        const QBrush baseBrush{QColor(m_electrodeColor)};
        const QBrush selBrush{QColor(blendHex(m_selectedColor, QStringLiteral("#ffffff"), 0.08))};

        QPen basePen(QColor(m_electrodeOutline), 1.1);
        QPen selPen(QColor(m_selectedColor), 2.2);
        basePen.setCosmetic(true);
        selPen.setCosmetic(true);

        for (auto it = m_itemsByIdx.cbegin(); it != m_itemsByIdx.cend(); ++it) {
            ElectrodeRectItem *item = it.value();
            if (item->isSelected()) {
                item->setBrush(selBrush);
                item->setPen(selPen);
            } else {
                item->setBrush(baseBrush);
                item->setPen(basePen);
            }
        }
    }

    void onSceneSelectionChanged() {
        refreshItemStyles();
        if (m_syncing) {
            return;
        }
        if (m_pairSelectionChanged) {
            m_pairSelectionChanged(selectedPairsFromScene());
        }
    }
};

ChannelMapPanel::ChannelMapPanel(ChannelAddressState *channelState, QWidget *parent)
    : QWidget(parent), m_channelState(channelState) {
    auto *root = new QVBoxLayout(this);

    auto *splitter = new QSplitter(Qt::Horizontal);
    root->addWidget(splitter, 1);

    auto *leftWrap = new QWidget;
    auto *left = new QVBoxLayout(leftWrap);
    left->setContentsMargins(0, 0, 0, 0);
    splitter->addWidget(leftWrap);

    auto *mapGrp = new QGroupBox(QStringLiteral("1024通道分布 (实体芯片视图)"));
    auto *mapLayout = new QVBoxLayout(mapGrp);
    auto *tip = new QLabel(QStringLiteral("支持单点选择、Ctrl多选、框选；Ctrl+滚轮缩放；选中颜色与当前主题联动。"));
    tip->setWordWrap(true);
    mapLayout->addWidget(tip);

    auto *zoomBar = new QHBoxLayout;
    zoomBar->addWidget(new QLabel(QStringLiteral("缩放")));
    auto *btnZoomOut = new QPushButton(QStringLiteral("-"));
    btnZoomOut->setFixedWidth(36);
    auto *btnZoomIn = new QPushButton(QStringLiteral("+"));
    btnZoomIn->setFixedWidth(36);
    auto *btnZoomFit = new QPushButton(QStringLiteral("适应窗口"));

    m_zoomSlider = new QSlider(Qt::Horizontal);
    m_zoomSlider->setRange(20, 500);
    m_zoomSlider->setValue(100);
    m_zoomLabel = new QLabel(QStringLiteral("100%"));
    m_zoomLabel->setMinimumWidth(52);

    zoomBar->addWidget(btnZoomOut);
    zoomBar->addWidget(btnZoomIn);
    zoomBar->addWidget(m_zoomSlider, 1);
    zoomBar->addWidget(m_zoomLabel);
    zoomBar->addWidget(btnZoomFit);
    mapLayout->addLayout(zoomBar);

    m_mapView = new ElectrodeMapView;
    m_mapView->setMinimumSize(1080, 700);
    m_mapView->setOnPairSelectionChanged([this](const QSet<QPair<int, int>> &pairs) { onMapPairsChanged(pairs); });
    m_mapView->setOnElectrodeClicked([this](const QVariantMap &info) { onElectrodeClicked(info); });
    m_mapView->setOnZoomChanged([this](int zoomPercent) { onZoomChanged(zoomPercent); });
    mapLayout->addWidget(m_mapView, 1);
    left->addWidget(mapGrp, 1);

    auto *rightWrap = new QWidget;
    rightWrap->setMinimumWidth(460);
    rightWrap->setMaximumWidth(620);
    auto *rightLayout = new QVBoxLayout(rightWrap);
    rightLayout->setContentsMargins(0, 0, 0, 0);
    splitter->addWidget(rightWrap);

    splitter->setStretchFactor(0, 9);
    splitter->setStretchFactor(1, 4);
    splitter->setSizes({1980, 500});

    auto *batchGrp = new QGroupBox(QStringLiteral("快速选择"));
    auto *bf = new QGridLayout(batchGrp);
    bf->addWidget(new QLabel(QStringLiteral("Block范围(0-63)")), 0, 0);
    m_blockRangeEdit = new QLineEdit(QStringLiteral("0-63"));
    bf->addWidget(m_blockRangeEdit, 0, 1, 1, 3);

    bf->addWidget(new QLabel(QStringLiteral("Local Channel")), 1, 0);
    for (int i = 0; i < 4; ++i) {
        auto *cb = new QCheckBox(QString::number(i, 2).rightJustified(2, QLatin1Char('0')));
        cb->setChecked(true);
        m_localChecks.push_back(cb);
        bf->addWidget(cb, 1, 1 + i);
    }

    auto *btnBatchSelect = new QPushButton(QStringLiteral("批量选中"));
    auto *btnBatchUnselect = new QPushButton(QStringLiteral("批量取消"));
    auto *btnSelectAll = new QPushButton(QStringLiteral("全选"));
    auto *btnClearAll = new QPushButton(QStringLiteral("清空"));
    bf->addWidget(btnBatchSelect, 2, 0);
    bf->addWidget(btnBatchUnselect, 2, 1);
    bf->addWidget(btnSelectAll, 2, 2);
    bf->addWidget(btnClearAll, 2, 3);

    bf->addWidget(new QLabel(QStringLiteral("按全局通道选(0-255)")), 3, 0);
    m_globalEdit = new QLineEdit;
    m_globalEdit->setPlaceholderText(QStringLiteral("例如: 0-31,64,128-140"));
    bf->addWidget(m_globalEdit, 3, 1, 1, 2);
    auto *btnApplyGlobal = new QPushButton(QStringLiteral("应用"));
    bf->addWidget(btnApplyGlobal, 3, 3);
    rightLayout->addWidget(batchGrp);

    auto *infoGrp = new QGroupBox(QStringLiteral("选中电极信息"));
    auto *info = new QFormLayout(infoGrp);
    m_blockLabel = new QLabel(QStringLiteral("-"));
    m_localLabel = new QLabel(QStringLiteral("-"));
    m_globalLabel = new QLabel(QStringLiteral("-"));
    m_electrodeLabel = new QLabel(QStringLiteral("-"));
    m_spiBitsLabel = new QLabel(QStringLiteral("-"));
    info->addRow(QStringLiteral("Block"), m_blockLabel);
    info->addRow(QStringLiteral("Local Channel"), m_localLabel);
    info->addRow(QStringLiteral("Global Channel"), m_globalLabel);
    info->addRow(QStringLiteral("Electrode"), m_electrodeLabel);
    info->addRow(QStringLiteral("SPI Addr(8b+2b)"), m_spiBitsLabel);

    m_historyList = new QListWidget;
    m_historyList->setMaximumHeight(160);
    auto *infoBox = new QVBoxLayout;
    infoBox->addWidget(infoGrp);
    infoBox->addWidget(new QLabel(QStringLiteral("点击历史(最新在上)")));
    infoBox->addWidget(m_historyList);
    rightLayout->addLayout(infoBox);

    auto *rightGrp = new QGroupBox(QStringLiteral("地址输出"));
    auto *right = new QVBoxLayout(rightGrp);
    m_selCountLabel = new QLabel(QStringLiteral("已选: 0"));
    right->addWidget(m_selCountLabel);

    auto *btnGetAddr = new QPushButton(QStringLiteral("Get Channel Address"));
    auto *btnCopyAddr = new QPushButton(QStringLiteral("复制结果"));
    right->addWidget(btnGetAddr);
    right->addWidget(btnCopyAddr);

    m_outputEdit = new QPlainTextEdit;
    m_outputEdit->setReadOnly(true);
    right->addWidget(m_outputEdit, 1);
    rightLayout->addWidget(rightGrp, 1);

    connect(btnBatchSelect, &QPushButton::clicked, this, &ChannelMapPanel::onBatchModifySelect);
    connect(btnBatchUnselect, &QPushButton::clicked, this, &ChannelMapPanel::onBatchModifyUnselect);
    connect(btnSelectAll, &QPushButton::clicked, this, &ChannelMapPanel::onSelectAll);
    connect(btnClearAll, &QPushButton::clicked, m_channelState, &ChannelAddressState::clear);
    connect(btnApplyGlobal, &QPushButton::clicked, this, &ChannelMapPanel::onApplyGlobalChannels);
    connect(btnGetAddr, &QPushButton::clicked, this, &ChannelMapPanel::onRefreshOutput);
    connect(btnCopyAddr, &QPushButton::clicked, this, &ChannelMapPanel::onCopyOutput);

    connect(btnZoomOut, &QPushButton::clicked, this, [this]() { m_mapView->zoomOut(); });
    connect(btnZoomIn, &QPushButton::clicked, this, [this]() { m_mapView->zoomIn(); });
    connect(btnZoomFit, &QPushButton::clicked, this, [this]() { m_mapView->fitToChip(); });
    connect(m_zoomSlider, &QSlider::valueChanged, this, [this](int value) { m_mapView->setZoomPercent(value); });

    connect(m_channelState, &ChannelAddressState::selectionChanged, this, &ChannelMapPanel::syncUiFromState);
    syncUiFromState();
}

QSet<int> ChannelMapPanel::parseIntRanges(const QString &text, int minimum, int maximum, bool *ok, QString *error) const {
    QSet<int> result;
    *ok = true;
    error->clear();

    const QString trimmed = text.trimmed();
    if (trimmed.isEmpty()) {
        return result;
    }

    const QStringList parts = trimmed.split(',', Qt::SkipEmptyParts);
    for (const QString &part : parts) {
        const QString token = part.trimmed();
        if (token.isEmpty()) {
            continue;
        }

        if (token.contains('-')) {
            const QStringList ab = token.split('-', Qt::KeepEmptyParts);
            if (ab.size() != 2) {
                *ok = false;
                *error = QStringLiteral("区间格式错误: %1").arg(token);
                return {};
            }

            bool okA = false;
            bool okB = false;
            int a = ab[0].trimmed().toInt(&okA);
            int b = ab[1].trimmed().toInt(&okB);
            if (!okA || !okB) {
                *ok = false;
                *error = QStringLiteral("区间数字错误: %1").arg(token);
                return {};
            }
            if (a > b) {
                std::swap(a, b);
            }
            for (int v = a; v <= b; ++v) {
                if (v >= minimum && v <= maximum) {
                    result.insert(v);
                }
            }
        } else {
            bool okV = false;
            const int v = token.toInt(&okV);
            if (!okV) {
                *ok = false;
                *error = QStringLiteral("数字格式错误: %1").arg(token);
                return {};
            }
            if (v >= minimum && v <= maximum) {
                result.insert(v);
            }
        }
    }

    return result;
}

void ChannelMapPanel::onZoomChanged(int zoomPercent) {
    m_zoomLabel->setText(QStringLiteral("%1%").arg(zoomPercent));
    m_zoomSlider->blockSignals(true);
    m_zoomSlider->setValue(zoomPercent);
    m_zoomSlider->blockSignals(false);
}

void ChannelMapPanel::onMapPairsChanged(const QSet<QPair<int, int>> &pairs) {
    m_channelState->setSelectedPairs(pairs);
}

void ChannelMapPanel::onElectrodeClicked(const QVariantMap &info) {
    const int block = info.value(QStringLiteral("block"), -1).toInt();
    const int local = info.value(QStringLiteral("local_channel"), 0).toInt();
    const int global = info.value(QStringLiteral("global_channel"), -1).toInt();
    const int electrode = info.value(QStringLiteral("electrode_global"), -1).toInt();
    const QString addressBits = info.value(QStringLiteral("address_bits")).toString();

    m_blockLabel->setText(block >= 0 ? QString::number(block) : QStringLiteral("-"));
    m_localLabel->setText(QString::number(local, 2).rightJustified(2, QLatin1Char('0')));
    m_globalLabel->setText(global >= 0 ? QString::number(global) : QStringLiteral("-"));
    m_electrodeLabel->setText(electrode >= 0 ? QString::number(electrode) : QStringLiteral("-"));
    m_spiBitsLabel->setText(addressBits.isEmpty() ? QStringLiteral("-") : addressBits);

    const QString line = QStringLiteral("B%1 | L%2 | G%3 | %4")
                             .arg(block, 2, 10, QLatin1Char('0'))
                             .arg(QString::number(local, 2).rightJustified(2, QLatin1Char('0')))
                             .arg(global, 3, 10, QLatin1Char('0'))
                             .arg(addressBits);
    m_historyList->insertItem(0, line);
    while (m_historyList->count() > 300) {
        delete m_historyList->takeItem(m_historyList->count() - 1);
    }
}

void ChannelMapPanel::onBatchModifySelect() {
    batchModify(true);
}

void ChannelMapPanel::onBatchModifyUnselect() {
    batchModify(false);
}

void ChannelMapPanel::batchModify(bool makeSelected) {
    bool ok = false;
    QString error;
    const QSet<int> blocks = parseIntRanges(m_blockRangeEdit->text(), 0, 63, &ok, &error);
    if (!ok) {
        QMessageBox::warning(this, QStringLiteral("输入错误"), QStringLiteral("Block范围解析失败: %1").arg(error));
        return;
    }
    if (blocks.isEmpty()) {
        QMessageBox::warning(this, QStringLiteral("输入错误"), QStringLiteral("Block范围为空"));
        return;
    }

    QSet<int> locals;
    for (int i = 0; i < m_localChecks.size(); ++i) {
        if (m_localChecks[i]->isChecked()) {
            locals.insert(i);
        }
    }
    if (locals.isEmpty()) {
        QMessageBox::warning(this, QStringLiteral("输入错误"), QStringLiteral("请至少勾选一个Local Channel"));
        return;
    }

    QSet<QPair<int, int>> selected;
    const QVector<QPair<int, int>> current = m_channelState->selectedPairs();
    for (const QPair<int, int> &pair : current) {
        selected.insert(pair);
    }

    for (int b : blocks) {
        for (int l : locals) {
            if (makeSelected) {
                selected.insert({b, l});
            } else {
                selected.remove({b, l});
            }
        }
    }

    m_channelState->setSelectedPairs(selected);
}

void ChannelMapPanel::onSelectAll() {
    QSet<QPair<int, int>> selected;
    for (int b = 0; b < 64; ++b) {
        for (int l = 0; l < 4; ++l) {
            selected.insert({b, l});
        }
    }
    m_channelState->setSelectedPairs(selected);
}

void ChannelMapPanel::onApplyGlobalChannels() {
    bool ok = false;
    QString error;
    const QSet<int> channels = parseIntRanges(m_globalEdit->text(), 0, 255, &ok, &error);
    if (!ok) {
        QMessageBox::warning(this, QStringLiteral("输入错误"), QStringLiteral("全局通道解析失败: %1").arg(error));
        return;
    }

    QSet<QPair<int, int>> selected;
    const QVector<QPair<int, int>> current = m_channelState->selectedPairs();
    for (const QPair<int, int> &pair : current) {
        selected.insert(pair);
    }
    for (int ch : channels) {
        selected.insert({ch / 4, ch % 4});
    }
    m_channelState->setSelectedPairs(selected);
}

void ChannelMapPanel::onRefreshOutput() {
    const QVector<AddressRecord> records = m_channelState->selectedAddressRecords();
    if (records.isEmpty()) {
        m_outputEdit->setPlainText(QStringLiteral("未选择任何通道"));
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
    m_outputEdit->setPlainText(lines.join('\n'));
}

void ChannelMapPanel::onCopyOutput() {
    onRefreshOutput();
    QApplication::clipboard()->setText(m_outputEdit->toPlainText());
}

void ChannelMapPanel::syncUiFromState() {
    QSet<QPair<int, int>> selected;
    const QVector<QPair<int, int>> pairs = m_channelState->selectedPairs();
    for (const QPair<int, int> &pair : pairs) {
        selected.insert(pair);
    }
    m_mapView->setSelectedPairs(selected);

    m_selCountLabel->setText(
        QStringLiteral("已选: %1  (可映射global channel总数: %2)").arg(selected.size()).arg(m_channelState->selectedGlobalChannels().size()));
    onRefreshOutput();
}

void ChannelMapPanel::setMapTheme(const QMap<QString, QString> &palette) {
    m_mapView->setThemePalette(palette);
}

}  // namespace ccv2
