#pragma once

#include <QMap>
#include <QVector>

#include <memory>

#include "data/ring_buffer.h"

namespace ccv2 {

class DataStore {
public:
    void reset(const QVector<int> &channels, int capacity);
    void appendChannelValues(int ch, const QVector<qint32> &values);

    bool contains(int ch) const;
    RingBuffer *buffer(int ch);
    QVector<int> channels() const;

private:
    QMap<int, std::shared_ptr<RingBuffer>> m_buffers;
};

}  // namespace ccv2
