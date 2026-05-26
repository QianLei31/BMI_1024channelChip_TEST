#pragma once

#include <QMutex>
#include <QPair>
#include <QVector>

namespace ccv2 {

class RingBuffer {
public:
    explicit RingBuffer(int capacity = 65536)
        : m_capacity(capacity), m_data(capacity, 0), m_writeIdx(0), m_size(0), m_totalWritten(0) {}

    void appendMany(const QVector<qint32> &values) {
        if (values.isEmpty()) {
            return;
        }

        QVector<qint32> clipped = values;
        if (clipped.size() >= m_capacity) {
            clipped = clipped.sliced(clipped.size() - m_capacity);
        }

        QMutexLocker locker(&m_mutex);
        const int n = clipped.size();
        const int first = qMin(n, m_capacity - m_writeIdx);
        for (int i = 0; i < first; ++i) {
            m_data[m_writeIdx + i] = clipped[i];
        }

        const int remaining = n - first;
        for (int i = 0; i < remaining; ++i) {
            m_data[i] = clipped[first + i];
        }

        m_writeIdx = (m_writeIdx + n) % m_capacity;
        m_size = qMin(m_capacity, m_size + n);
        m_totalWritten += n;
    }

    QPair<QVector<qint64>, QVector<qint32>> getLatest(int nPoints) const {
        QMutexLocker locker(&m_mutex);
        if (m_size < nPoints || nPoints <= 0) {
            return {QVector<qint64>(), QVector<qint32>()};
        }

        const int start = (m_writeIdx - nPoints + m_capacity) % m_capacity;
        QVector<qint32> values;
        values.reserve(nPoints);

        if (start + nPoints <= m_capacity) {
            for (int i = 0; i < nPoints; ++i) {
                values.push_back(m_data[start + i]);
            }
        } else {
            const int first = m_capacity - start;
            for (int i = 0; i < first; ++i) {
                values.push_back(m_data[start + i]);
            }
            for (int i = 0; i < nPoints - first; ++i) {
                values.push_back(m_data[i]);
            }
        }

        QVector<qint64> indices;
        indices.reserve(nPoints);
        const qint64 startIdx = m_totalWritten - nPoints;
        for (int i = 0; i < nPoints; ++i) {
            indices.push_back(startIdx + i);
        }
        return {indices, values};
    }

private:
    int m_capacity;
    QVector<qint32> m_data;
    int m_writeIdx;
    int m_size;
    qint64 m_totalWritten;
    mutable QMutex m_mutex;
};

}  // namespace ccv2
