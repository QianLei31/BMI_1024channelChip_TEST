import sys
import socket
import binascii
import os
import numpy as np
from numpy import sin, pi
from scipy import signal
import spi_mode
from spi_mode import *
from fun_cal_sndr import cal_sndr
import matplotlib.pyplot as plt
from matplotlib.offsetbox import AnchoredText
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QTextEdit, QPushButton, QFrame
)

HOST = '192.168.2.10'
PORT = 7
SIZE_TCPIP_SEND_BUF_TRUNK = 4096
TCP_PACKET_CT = SIZE_TCPIP_SEND_BUF_TRUNK
TCP_TOTAL = 1 * 1024 * 1024 * 2048
Count_max = TCP_TOTAL // TCP_PACKET_CT
BYTES_DATA_POINTS = 4
ADC_bits = 12
fs = 10000000 / 12 / 80
fb = fs // 2
dt_read_cnt = 15
NUM_DATA_POINTS_READ = dt_read_cnt * SIZE_TCPIP_SEND_BUF_TRUNK // 4
data_recv_init = bytearray()
data_rec = np.zeros(NUM_DATA_POINTS_READ)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("TEST_CHIP")
        self.setGeometry(100, 100, 1200, 800)

        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)

        # Console Output
        self.console_output = QTextEdit()
        self.console_output.setReadOnly(True)
        console_layout = QHBoxLayout()
        console_layout.addWidget(self.console_output)
        main_layout.addLayout(console_layout)

        # SPI Command Entry
        spi_layout = QHBoxLayout()
        self.label_spi_cmd = QLabel("SPI 命令：")
        spi_layout.addWidget(self.label_spi_cmd)
        self.entry_spi_cmd = QLineEdit()
        spi_layout.addWidget(self.entry_spi_cmd)
        self.button_spi = QPushButton("Send SPI")
        self.button_spi.clicked.connect(self.spi_mode)
        spi_layout.addWidget(self.button_spi)
        main_layout.addLayout(spi_layout)

        # Clear Console Button
        self.button_clear_output = QPushButton("Clear Console")
        self.button_clear_output.clicked.connect(self.clear_console_output)
        main_layout.addWidget(self.button_clear_output)

        # Set Mode
        set_layout = QHBoxLayout()
        self.lable_entry_block = QLabel("Read Block:")
        set_layout.addWidget(self.lable_entry_block)
        self.entry_block = QLineEdit()
        set_layout.addWidget(self.entry_block)
        self.button_set = QPushButton("Set Channel")
        self.button_set.clicked.connect(self.set_mode)
        set_layout.addWidget(self.button_set)
        main_layout.addLayout(set_layout)

        # Read Mode Buttons
        read_layout = QHBoxLayout()
        self.button_read_dt = QPushButton("DT_Read")
        self.button_read_dt.clicked.connect(self.dt_read_mode)
        read_layout.addWidget(self.button_read_dt)
        self.button_read_ct = QPushButton("CT_Read")
        self.button_read_ct.clicked.connect(self.ct_read_mode_new)
        read_layout.addWidget(self.button_read_ct)
        main_layout.addLayout(read_layout)

        # Save Data Button
        self.button_save = QPushButton("Save Data")
        self.button_save.clicked.connect(self.save_data)
        main_layout.addWidget(self.button_save)

        # Additional Controls
        self.create_additional_controls(main_layout)

    def create_additional_controls(self, main_layout):
        # Adder Entry
        adder_layout = QHBoxLayout()
        self.adder_label = QLabel("adder:")
        adder_layout.addWidget(self.adder_label)
        self.adder_entry = QLineEdit()
        adder_layout.addWidget(self.adder_entry)
        main_layout.addLayout(adder_layout)

        # Data Entry
        data_layout = QHBoxLayout()
        self.data_label = QLabel("data:")
        data_layout.addWidget(self.data_label)
        self.data_entry = QLineEdit()
        data_layout.addWidget(self.data_entry)
        main_layout.addLayout(data_layout)

        # Stim ELECTRODE
        stim_ele_layout = QHBoxLayout()
        self.Stim_ELE_lable = QLabel("Stim_ele(/channel):")
        stim_ele_layout.addWidget(self.Stim_ELE_lable)
        self.Stim_ELE_entry = QLineEdit()
        stim_ele_layout.addWidget(self.Stim_ELE_entry)
        main_layout.addLayout(stim_ele_layout)

        # Stim AMP
        stim_amp_layout = QHBoxLayout()
        self.Stim_AMP_lable = QLabel("Stim_amp(9bit):")
        stim_amp_layout.addWidget(self.Stim_AMP_lable)
        self.Stim_AMP_entry = QLineEdit()
        stim_amp_layout.addWidget(self.Stim_AMP_entry)
        main_layout.addLayout(stim_amp_layout)

        # Function Buttons
        functions_layout = QHBoxLayout()
        functions_frame = QFrame()
        functions_layout_frame = QVBoxLayout()
        functions_frame.setLayout(functions_layout_frame)
        main_layout.addWidget(functions_frame)

        function_buttons = [
            ("Analog Reset", "Analog_Reset"),
            ("Analog Remove Reset", "Analog_RemoveReset"),
            ("Global DAC On", "Global_DAC_On"),
            ("Global DAC Off", "Global_DAC_Off"),
            ("SET CBOK LOW", "SET_CBOK_LOW"),
            ("Write STIM", "Write_STIM"),
            ("Read STIM", "Read_STIM"),
            ("Write REC", "Write_REC"),
            ("Read REC", "Read_REC"),
            ("Dummy", "Dummy")
        ]

        for text, method in function_buttons:
            button = QPushButton(text)
            button.clicked.connect(lambda _, m=method: self.call_spi_mode_function(m))
            functions_layout_frame.addWidget(button)

        function_buttons1 = [
            ("STIM_ELE1", "Stim_ELE1"),
            ("STIM_ELE2", "Stim_ELE2"),
            ("STIM_ELE5", "Stim_ELE5"),
            ("STIM_ELE6", "Stim_ELE6"),
            ("STIM_ELE11", "Stim_ELE11"),
            ("STIM_ELE12", "Stim_ELE12"),
            ("STIM_ELE13", "Stim_ELE13"),
            ("STIM_ELE14", "Stim_ELE14"),
            ("STIM_Multi", "Stim_Multi")
        ]

        for text, method in function_buttons1:
            button = QPushButton(text)
            button.clicked.connect(lambda _, m=method: self.call_spi_mode_function(m))
            functions_layout_frame.addWidget(button)

    def call_spi_mode_function(self, method_name):
        method = getattr(spi_mode, method_name, None)
        if method:
            console_output = self.console_output
            if method_name in ["Write_STIM", "Read_STIM", "Write_REC", "Read_REC"]:
                adder = int(self.adder_entry.text(), 16)
                if method_name.startswith("Write"):
                    data = int(self.data_entry.text(), 16)
                    method(console_output, adder, data)
                else:
                    method(console_output, adder)
            elif method_name == "Stim_Multi":
                stim_ele = int(self.Stim_ELE_entry.text())
                stim_amp = int(self.Stim_AMP_entry.text())
                method(console_output, stim_ele, stim_amp)
            elif method_name.startswith("Stim_ELE"):
                method(console_output)
            else:
                method(console_output)

    def save_data(self):
        global data_recv_init
        desdir = r"d:\testchip_results"
        strPathSave = desdir + "/" + "NL"
        os.makedirs(strPathSave, exist_ok=True)
        str_file_write = strPathSave + "/" + "ADC_DATA" + ".bin"
        if len(data_recv_init) == 0:
            self.console_output.append("No data to save\n")
            self.console_output.append(f": {(data_recv_init[1:])}\n")
            return
        else:
            with open(str_file_write, "ab+") as h_file_results:
                h_file_results.write(data_recv_init)
            self.console_output.append(f"Save data to {str_file_write}\n")

    def process_data(self, data):
        values = np.zeros(len(data) // 4)
        for i in range(0, len(data), 4):
            values[i // 4] = int.from_bytes(data[i:i + 4], byteorder='little')
        return values

    def set_mode(self):
        # 配置读取的通道
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((HOST, PORT))
            block_data = self.entry_block.text()
            binary_data = bytearray(int(block_data[i:i + 8], 2) for i in range(0, len(block_data), 8))
            hex_data = binascii.hexlify(binary_data).decode()
            message = "set" + hex_data
            self.console_output.append(f"{message}\n")
            s.sendall(message.encode())
        except Exception as e:
            self.console_output.append(f"Connect Error: {e}\n")
        finally:
            s.close()

    def dt_read_mode(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((HOST, PORT))
            message = "read"
            cnt = 0
            s.sendall(message.encode())
            data_rec = np.zeros(TCP_TOTAL // 4)
            while cnt < Count_max:
                recv_data = self.recieve_tcpip(s, SIZE_TCPIP_SEND_BUF_TRUNK)
                data_recv_init.extend(recv_data)
                self.console_output.append(f"Received amount: {len(recv_data)}\n")
                data_list = np.array(self.process_data(recv_data)) / 4096 * 1.8
                data_rec[cnt * SIZE_TCPIP_SEND_BUF_TRUNK // 4:(cnt + 1) * SIZE_TCPIP_SEND_BUF_TRUNK // 4] = data_list
                cnt += 1

            fs = 10000000 / 12 / 80
            cal_sndr(data_rec, fs)
        except Exception as e:
            self.console_output.append(f"Connect Error: {e}\n")
        finally:
            s.close()

    def recieve_tcpip(self, sock, size):
        chunks = []
        bytes_recd = 0
        while bytes_recd < size:
            chunk = sock.recv(min(size - bytes_recd, 2048))
            if chunk == b'':
                raise RuntimeError("socket connection broken")
            chunks.append(chunk)
            bytes_recd += len(chunk)
        return b''.join(chunks)

    def ct_read_mode_new(self):
        global data_recv_init
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((HOST, PORT))
            message = "read"
            cnt = 0
            s.sendall(message.encode())
            data_rec = np.zeros(TCP_TOTAL // 4)
            while cnt < Count_max:
                recv_data = self.recieve_tcpip(s, SIZE_TCPIP_SEND_BUF_TRUNK)
                data_recv_init.extend(recv_data)
                self.console_output.append(f"Received amount: {len(recv_data)}\n")
                data_list = np.array(self.process_data(recv_data)) / 4096 * 1.8
                data_rec[cnt * SIZE_TCPIP_SEND_BUF_TRUNK // 4:(cnt + 1) * SIZE_TCPIP_SEND_BUF_TRUNK // 4] = data_list
                cnt += 1

            fs = 10000000 / 12 / 80
            cal_sndr(data_rec, fs)
        except Exception as e:
            self.console_output.append(f"Connect Error: {e}\n")
        finally:
            s.close()

    def clear_console_output(self):
        self.console_output.clear()

    def spi_mode(self):
        spi_cmd = self.entry_spi_cmd.text()
        spi_mode.spi_mode(spi_cmd)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    mainWin = MainWindow()
    mainWin.show()
    sys.exit(app.exec_())
