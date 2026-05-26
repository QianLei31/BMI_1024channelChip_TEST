#include "config/config_manager.h"

#include <QCoreApplication>
#include <QDir>
#include <QFileInfo>
#include <QSettings>

namespace ccv2 {

ConfigManager::ConfigManager(const QString &fileName) : m_fileName(fileName) {}

QString ConfigManager::path() const {
    return QDir(QCoreApplication::applicationDirPath()).filePath(m_fileName);
}

ConfigMap ConfigManager::defaults() {
    ConfigMap cfg;
    cfg[QStringLiteral("Network")] = {{QStringLiteral("host"), QStringLiteral("192.168.2.10")}, {QStringLiteral("port"), QStringLiteral("7")}};
    cfg[QStringLiteral("Signal")] = {{QStringLiteral("sampling_rate"), QStringLiteral("20000")}, {QStringLiteral("fft_points"), QStringLiteral("16384")}};
    cfg[QStringLiteral("Paths")] = {{QStringLiteral("save_dir"), QStringLiteral("d:/ADC_data")}};
    cfg[QStringLiteral("UI")] = {
        {QStringLiteral("theme"), QStringLiteral("Deep Sea Blue")},
        {QStringLiteral("window_width"), QStringLiteral("1920")},
        {QStringLiteral("window_height"), QStringLiteral("1100")},
    };
    cfg[QStringLiteral("Stimulator")] = {
        {QStringLiteral("block"), QStringLiteral("00000000")},
        {QStringLiteral("addr_channel"), QStringLiteral("00")},
        {QStringLiteral("amplitude"), QStringLiteral("000000000")},
        {QStringLiteral("polarity"), QStringLiteral("00 (Output 0)")},
        {QStringLiteral("compensate"), QStringLiteral("0 (Disable)")},
        {QStringLiteral("step"), QStringLiteral("0 (4nA)")},
        {QStringLiteral("dac_channel"), QStringLiteral("00")},
    };
    return cfg;
}

bool ConfigManager::save(const ConfigMap &cfg) const {
    QSettings settings(path(), QSettings::IniFormat);
    settings.clear();
    for (auto secIt = cfg.cbegin(); secIt != cfg.cend(); ++secIt) {
        settings.beginGroup(secIt.key());
        for (auto kvIt = secIt.value().cbegin(); kvIt != secIt.value().cend(); ++kvIt) {
            settings.setValue(kvIt.key(), kvIt.value());
        }
        settings.endGroup();
    }
    settings.sync();
    return settings.status() == QSettings::NoError;
}

ConfigMap ConfigManager::load() const {
    if (!QFileInfo::exists(path())) {
        save(defaults());
    }

    QSettings settings(path(), QSettings::IniFormat);
    ConfigMap cfg;
    const QStringList groups = settings.childGroups();
    for (const QString &group : groups) {
        settings.beginGroup(group);
        ConfigSection sec;
        const QStringList keys = settings.childKeys();
        for (const QString &key : keys) {
            sec[key] = settings.value(key).toString();
        }
        settings.endGroup();
        cfg[group] = sec;
    }

    const ConfigMap def = defaults();
    for (auto secIt = def.cbegin(); secIt != def.cend(); ++secIt) {
        if (!cfg.contains(secIt.key())) {
            cfg[secIt.key()] = secIt.value();
            continue;
        }
        for (auto kvIt = secIt.value().cbegin(); kvIt != secIt.value().cend(); ++kvIt) {
            if (!cfg[secIt.key()].contains(kvIt.key())) {
                cfg[secIt.key()][kvIt.key()] = kvIt.value();
            }
        }
    }
    return cfg;
}

}  // namespace ccv2
