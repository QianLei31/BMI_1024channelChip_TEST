#include "data/data_store.h"

namespace ccv2 {

void DataStore::reset(const QVector<int> &channels, int capacity) {
    m_buffers.clear();
    for (int ch : channels) {
        m_buffers.insert(ch, std::make_shared<RingBuffer>(capacity));
    }
}

void DataStore::appendChannelValues(int ch, const QVector<qint32> &values) {
    auto it = m_buffers.find(ch);
    if (it == m_buffers.end()) {
        return;
    }
    it.value()->appendMany(values);
}

bool DataStore::contains(int ch) const {
    return m_buffers.contains(ch);
}

RingBuffer *DataStore::buffer(int ch) {
    auto it = m_buffers.find(ch);
    if (it == m_buffers.end()) {
        return nullptr;
    }
    return it.value().get();
}

QVector<int> DataStore::channels() const {
    return m_buffers.keys().toVector();
}

}  // namespace ccv2
