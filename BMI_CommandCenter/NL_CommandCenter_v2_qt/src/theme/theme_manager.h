#pragma once

#include <QMap>
#include <QString>
#include <QStringList>

namespace ccv2 {

enum class ThemeStyle {
    NeuralDark = 0,
};

class ThemeManager {
public:
    static QStringList themeNames();
    static QString styleSheetFor(ThemeStyle style);
    static ThemeStyle fromIndex(int idx);

    struct ColorTokens {
        QString appBg;
        QString cardBg;
        QString cardBorder;
        QString primaryAccent;
        QString secondaryAccent;
        QString success;
        QString warning;
        QString error;
        QString textPrimary;
        QString textSecondary;
        QString navBg;
        QString navSelected;
        QString inputBg;
        QString plotBg;
        QString plotAxis;
        QString waveLine;
        QString statusBarBg;
    };

    static ColorTokens colors();
};

}  // namespace ccv2
