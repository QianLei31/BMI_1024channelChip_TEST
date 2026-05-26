#pragma once

#include <QFile>
#include <QMutex>
#include <QString>

namespace ccv2 {

class SessionRecorder {
public:
    QString start(const QString &baseDir, const QString &folderName);
    void write(const QByteArray &rawBytes);
    void stop();

private:
    QFile m_file;
    QMutex m_mutex;
};

}  // namespace ccv2
