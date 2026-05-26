#include <QApplication>

#include "ui/command_center_main_window.h"

int main(int argc, char *argv[]) {
    QApplication app(argc, argv);
    ccv2::CommandCenterMainWindow window;
    window.show();
    return app.exec();
}
