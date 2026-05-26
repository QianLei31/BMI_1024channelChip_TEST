#include "io/session_recorder.h"

#include <QDateTime>
#include <QDir>
#include <QTextStream>

namespace ccv2 {

QString SessionRecorder::start(const QString &baseDir, const QString &folderName) {
    QMutexLocker locker(&m_mutex);
    if (m_file.isOpen()) {
        m_file.close();
    }

    QDir base(baseDir);
    if (!base.exists()) {
        base.mkpath(QStringLiteral("."));
    }

    const QString folderPath = base.filePath(folderName);
    QDir().mkpath(folderPath);

    m_file.setFileName(QDir(folderPath).filePath(QStringLiteral("ADC_DATA.bin")));
    if (!m_file.open(QIODevice::WriteOnly)) {
        return QString();
    }

    QFile meta(QDir(folderPath).filePath(QStringLiteral("metadata.txt")));
    if (meta.open(QIODevice::WriteOnly | QIODevice::Text)) {
        QTextStream ts(&meta);
        ts << "created_at: " << QDateTime::currentDateTime().toString(Qt::ISODate) << "\n";
        ts << "format: int32 little-endian interleaved 256ch\n";
    }

    return folderPath;
}

void SessionRecorder::write(const QByteArray &rawBytes) {
    QMutexLocker locker(&m_mutex);
    if (m_file.isOpen()) {
        m_file.write(rawBytes);
    }
}

void SessionRecorder::stop() {
    QMutexLocker locker(&m_mutex);
    if (m_file.isOpen()) {
        m_file.flush();
        m_file.close();
    }
}

}  // namespace ccv2
