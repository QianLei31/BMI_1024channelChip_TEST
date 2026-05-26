cmake_minimum_required(VERSION 3.20)
project(NL_CommandCenter_v2_qt LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)
set(CMAKE_AUTORCC ON)
set(CMAKE_AUTOUIC ON)

find_package(Qt6 QUIET COMPONENTS Core Gui Widgets Network)

# Fallback Qt discovery when no preset/environment selection is active.
if(NOT Qt6_FOUND)
    if(DEFINED ENV{Qt6_DIR})
        set(Qt6_DIR "$ENV{Qt6_DIR}")
    elseif(DEFINED ENV{QTDIR})
        list(APPEND CMAKE_PREFIX_PATH "$ENV{QTDIR}")
    endif()

    if(WIN32)
        file(GLOB _qt_roots LIST_DIRECTORIES true
            "E:/Qt/*"
            "E:/QT/*"
            "C:/Qt/*"
        )

        foreach(_qt_root IN LISTS _qt_roots)
            file(GLOB _qt_variants LIST_DIRECTORIES true
                "${_qt_root}/mingw_*"
                "${_qt_root}/msvc*"
            )

            foreach(_qt_variant IN LISTS _qt_variants)
                if(EXISTS "${_qt_variant}/lib/cmake/Qt6/Qt6Config.cmake")
                    list(PREPEND CMAKE_PREFIX_PATH "${_qt_variant}")
                    set(_qt_found TRUE)
                    break()
                endif()
            endforeach()

            if(_qt_found)
                break()
            endif()
        endforeach()
    endif()

    find_package(Qt6 REQUIRED COMPONENTS Core Gui Widgets Network)
endif()

include(CTest)

set(SOURCES
    src/main.cpp
    src/core/constants.h
    src/core/network_state.h
    src/core/channel_address_state.h
    src/core/channel_address_state.cpp
    src/config/config_manager.h
    src/config/config_manager.cpp
    src/core/threadsafe_queue.h
    src/data/ring_buffer.h
    src/data/data_store.h
    src/data/data_store.cpp
    src/io/session_recorder.h
    src/io/session_recorder.cpp
    src/network/tcp_receiver.h
    src/network/tcp_receiver.cpp
    src/network/data_sorter.h
    src/network/data_sorter.cpp
    src/network/socket_receiver2.h
    src/network/socket_receiver2.cpp
    src/network/replay_reader.h
    src/network/replay_reader.cpp
    src/network/sorter_worker.h
    src/network/sorter_worker.cpp
    src/signal/sndr_calculator.h
    src/signal/sndr_calculator.cpp
    src/theme/theme_manager.h
    src/theme/theme_manager.cpp
    src/core/channel_info.h
    src/ui/waveform_widget.h
    src/ui/waveform_widget.cpp
    src/ui/hardware_control_panel.h
    src/ui/hardware_control_panel.cpp
    src/ui/channel_map_panel.h
    src/ui/channel_map_panel.cpp
    src/ui/array_preview_panel.h
    src/ui/array_preview_panel.cpp
    src/ui/channel_analyzer_panel.h
    src/ui/channel_analyzer_panel.cpp
    src/ui/top_status_bar.h
    src/ui/top_status_bar.cpp
    src/ui/settings_dialog.h
    src/ui/settings_dialog.cpp
    src/ui/command_center_main_window.h
    src/ui/command_center_main_window.cpp
)

add_executable(${PROJECT_NAME} ${SOURCES})

target_include_directories(${PROJECT_NAME} PRIVATE src)

target_link_libraries(${PROJECT_NAME} PRIVATE
    Qt6::Core
    Qt6::Gui
    Qt6::Widgets
    Qt6::Network
)

if(WIN32)
    option(ENABLE_AUTO_QT_DEPLOY "Automatically copy Qt runtime DLLs next to executable" ON)
    if(ENABLE_AUTO_QT_DEPLOY)
        set(_windeployqt "")

        if(DEFINED ENV{WINDEPLOYQT_EXECUTABLE} AND EXISTS "$ENV{WINDEPLOYQT_EXECUTABLE}")
            set(_windeployqt "$ENV{WINDEPLOYQT_EXECUTABLE}")
        endif()

        if(NOT _windeployqt AND DEFINED Qt6_DIR)
            get_filename_component(_qt6_cmake_dir "${Qt6_DIR}" DIRECTORY)
            get_filename_component(_qt6_lib_dir "${_qt6_cmake_dir}" DIRECTORY)
            get_filename_component(_qt6_prefix "${_qt6_lib_dir}" DIRECTORY)
            set(_windeployqt_candidate "${_qt6_prefix}/bin/windeployqt.exe")
            if(EXISTS "${_windeployqt_candidate}")
                set(_windeployqt "${_windeployqt_candidate}")
            endif()
        endif()

        if(NOT _windeployqt)
            find_program(_windeployqt NAMES windeployqt.exe windeployqt
                HINTS
                    "E:/Qt/6.5.3/mingw_64/bin"
                    "E:/QT/6.5.3/mingw_64/bin"
                    "C:/Qt/6.5.3/mingw_64/bin"
            )
        endif()

        if(_windeployqt)
            add_custom_command(
                TARGET ${PROJECT_NAME}
                POST_BUILD
                COMMAND "${_windeployqt}" --dir "$<TARGET_FILE_DIR:${PROJECT_NAME}>" "$<TARGET_FILE:${PROJECT_NAME}>"
                COMMENT "Deploying Qt runtime DLLs next to executable"
                VERBATIM
            )
        else()
            message(WARNING "windeployqt not found; Qt DLL deployment is skipped.")
        endif()
    endif()
endif()

if(BUILD_TESTING)
    get_filename_component(_cxx_bin_dir "${CMAKE_CXX_COMPILER}" DIRECTORY)

    add_executable(ccv2_sndr_smoke
        tests/sndr_calculator_smoke.cpp
        src/signal/sndr_calculator.cpp
    )

    target_include_directories(ccv2_sndr_smoke PRIVATE src)

    target_link_libraries(ccv2_sndr_smoke PRIVATE
        Qt6::Core
    )

    add_test(
        NAME sndr_smoke
        COMMAND ${CMAKE_COMMAND} -E env
            "PATH=$<TARGET_FILE_DIR:Qt6::Core>\;${_cxx_bin_dir}\;$ENV{PATH}"
            $<TARGET_FILE:ccv2_sndr_smoke>
    )

    add_executable(ccv2_ui_pipeline_smoke
        tests/ui_pipeline_smoke.cpp
        src/network/data_sorter.cpp
        src/network/sorter_worker.cpp
        src/data/data_store.cpp
        src/io/session_recorder.cpp
        src/signal/sndr_calculator.cpp
        src/ui/waveform_widget.cpp
    )

    target_include_directories(ccv2_ui_pipeline_smoke PRIVATE src)

    target_link_libraries(ccv2_ui_pipeline_smoke PRIVATE
        Qt6::Core
        Qt6::Gui
        Qt6::Widgets
    )

    add_test(
        NAME ui_pipeline_smoke
        COMMAND ${CMAKE_COMMAND} -E env
            "QT_QPA_PLATFORM=offscreen"
            "QT_PLUGIN_PATH=$<TARGET_FILE_DIR:Qt6::Core>/../plugins"
            "PATH=$<TARGET_FILE_DIR:Qt6::Core>\;${_cxx_bin_dir}\;$ENV{PATH}"
            $<TARGET_FILE:ccv2_ui_pipeline_smoke>
    )
endif()
