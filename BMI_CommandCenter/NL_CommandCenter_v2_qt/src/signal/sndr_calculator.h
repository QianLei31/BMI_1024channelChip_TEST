#pragma once

#include <QString>
#include <QVector>

namespace ccv2 {

struct SndrResult {
    double sndrDb{0.0};
    double enob{0.0};
    double irn{0.0};
    double fin{0.0};
    QVector<double> fftData;
    QVector<double> fftFreq;
    double irnPowerDb{0.0};
    double thdDb{0.0};
    bool ok{false};
    QString error;
};

SndrResult calSndr(const QVector<double> &data, double fs, double fb, const QString &winType);

}  // namespace ccv2
