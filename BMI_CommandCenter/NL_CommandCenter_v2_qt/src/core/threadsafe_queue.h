#pragma once

#include <QMutex>
#include <QQueue>
#include <QWaitCondition>

namespace ccv2 {

template <typename T>
class ThreadSafeQueue {
public:
    explicit ThreadSafeQueue(int maxSize = 0) : m_maxSize(maxSize) {}

    void push(const T &item, bool dropOldestWhenFull = false) {
        QMutexLocker locker(&m_mutex);
        if (m_maxSize > 0 && m_queue.size() >= m_maxSize) {
            if (dropOldestWhenFull) {
                m_queue.dequeue();
            } else {
                return;
            }
        }
        m_queue.enqueue(item);
        m_cv.wakeOne();
    }

    bool pop(T &out, int timeoutMs) {
        QMutexLocker locker(&m_mutex);
        if (m_queue.isEmpty()) {
            if (!m_cv.wait(&m_mutex, timeoutMs)) {
                return false;
            }
            if (m_queue.isEmpty()) {
                return false;
            }
        }
        out = m_queue.dequeue();
        return true;
    }

    void clear() {
        QMutexLocker locker(&m_mutex);
        m_queue.clear();
    }

    int size() const {
        QMutexLocker locker(&m_mutex);
        return m_queue.size();
    }

private:
    mutable QMutex m_mutex;
    QWaitCondition m_cv;
    QQueue<T> m_queue;
    int m_maxSize;
};

}  // namespace ccv2
