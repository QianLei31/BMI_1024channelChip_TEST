import socket
import binascii
import tkinter as tk
from tkinter import ttk, messagebox
import ttkbootstrap as tkb
from ttkbootstrap.constants import *
import time
import os
import subprocess
import configparser
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

class ConfigManager:
    """Handles reading and writing the config.ini file robustly."""
    def __init__(self, filename='config.ini'):
        script_dir = os.path.dirname(os.path.realpath(__file__))
        self.path = os.path.join(script_dir, filename)
        self.config = configparser.ConfigParser()

    def load(self):
        """
        Loads configuration from the file.
        If the file doesn't exist, creates a default one.
        """
        if not os.path.exists(self.path):
            self.create_default_config()

        self.config.read(self.path)
        return {s: dict(self.config.items(s)) for s in self.config.sections()}

    def create_default_config(self):
        """Creates a default config.ini file if it's missing."""
        self.config['Network'] = {
            'host': '192.168.2.10',
            'port': '7'
        }
        self.config['Signal'] = {
            'sampling_rate': '10416.67',
            'fft_points': '16384'
        }
        self.config['Paths'] = {
            'save_dir': 'd:/ADC_data'
        }
        self.config['Stimulator'] = {
            'block': '00000000',
            'addr_channel': '00',
            'amplitude': '000000000',
            'polarity': '00 (Output 0)',
            'compensate': '0 (Disable)',
            'step': '0 (4nA)',
            'dac_channel': '00'
        }
        with open(self.path, 'w') as configfile:
            self.config.write(configfile)
        print(f"Default configuration file created at: {self.path}")

    def save(self, config_dict):
        """Saves a dictionary to the config file."""
        save_parser = configparser.ConfigParser()
        for section, values in config_dict.items():
            save_parser[section] = values
        
        with open(self.path, 'w') as configfile:
            save_parser.write(configfile)


class NeuralinkTesterApp(tkb.Window):
    def __init__(self, title="Neuralink Chip Tester (By QL)", themename="litera"):
        super().__init__(title=title, themename=themename)
        self.geometry("1800x1150")

        self.is_streaming = False
        self.ani = None
        self.fig = None
        self.stream_socket = None
        self.SIZE_TCPIP_SEND_BUF_TRUNK = 4096
        
        # Load configuration first, as it's needed for variable initialization
        self.config_manager = ConfigManager()
        self.app_config = self.config_manager.load()

        # --- Initialize Stimulator Variables from Config ---
        stim_defaults = self.app_config.get('Stimulator', {})
        self.stim_block_var = tk.StringVar(value=stim_defaults.get('block', '00000000'))
        self.stim_addr_channel_var = tk.StringVar(value=stim_defaults.get('addr_channel', '00'))
        self.stim_amplitude_var = tk.StringVar(value=stim_defaults.get('amplitude', '000000000'))
        self.stim_polarity_var = tk.StringVar(value=stim_defaults.get('polarity', '00 (Output 0)'))
        self.stim_compensate_var = tk.StringVar(value=stim_defaults.get('compensate', '0 (Disable)'))
        self.stim_step_var = tk.StringVar(value=stim_defaults.get('step', '0 (4nA)'))
        self.stim_dac_channel_var = tk.StringVar(value=stim_defaults.get('dac_channel', '00'))
        
        # --- Build UI ---
        main_pane = ttk.PanedWindow(self, orient=HORIZONTAL)
        main_pane.pack(fill=BOTH, expand=True, padx=10, pady=10)

        console_frame = ttk.Labelframe(main_pane, text="Console Output", padding=5)
        self.console_output = tk.Text(console_frame, height=10, wrap='word', font=("Consolas", 9))
        self.console_output.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar = ttk.Scrollbar(console_frame, orient=VERTICAL, command=self.console_output.yview)
        scrollbar.pack(side=RIGHT, fill=Y)
        self.console_output.config(yscrollcommand=scrollbar.set)
        main_pane.add(console_frame, weight=1)

        control_panel = ttk.Frame(main_pane)
        self.create_control_widgets(control_panel)
        main_pane.add(control_panel, weight=1)
        
        # Load attributes and set protocol after UI is built
        self.load_attributes_from_config()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_attributes_from_config(self):
        """Safely loads parameters from the config dictionary into class attributes."""
        self.HOST = self.app_config.get('Network', {}).get('host', 'localhost')
        self.PORT = int(self.app_config.get('Network', {}).get('port', 7))
        self.FS = float(self.app_config.get('Signal', {}).get('sampling_rate', 10416.67))
        self.FFT_POINTS = int(self.app_config.get('Signal', {}).get('fft_points', 16384))
        self.SAVE_DIR = self.app_config.get('Paths', {}).get('save_dir', 'd:/ADC_data')
        self.log("Configuration loaded successfully.")

    def create_control_widgets(self, parent):
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=BOTH, expand=True, padx=5, pady=5)
        
        tab1 = ttk.Frame(notebook, padding=10)
        self.create_setup_spi_tab(tab1)
        notebook.add(tab1, text="  Setup & SPI Control  ")

        tab2 = ttk.Frame(notebook, padding=10)
        self.create_sequences_tab(tab2)
        notebook.add(tab2, text="  Command Library  ")

        tab3 = ttk.Frame(notebook, padding=10)
        self.create_analysis_tab(tab3)
        notebook.add(tab3, text="  Analysis  ")

    def create_setup_spi_tab(self, parent):
        parent.columnconfigure(1, weight=1)
        config_frame = ttk.Labelframe(parent, text="Configuration (config.ini)", padding=10)
        config_frame.grid(row=0, column=0, columnspan=3, padx=5, pady=10, sticky='new')
        config_frame.columnconfigure(1, weight=1)

        self.config_vars = {}
        row = 0
        config_sections_to_display = ['Network', 'Signal', 'Paths']
        for section in config_sections_to_display:
            options = self.app_config.get(section, {})
            if not options: continue
            
            if row > 0:
                ttk.Separator(config_frame, orient=HORIZONTAL).grid(row=row, column=0, columnspan=2, sticky='ew', pady=5)
                row += 1
            
            for key, value in options.items():
                label_text = f"{section} / {key}:"
                ttk.Label(config_frame, text=label_text).grid(row=row, column=0, padx=5, pady=2, sticky='w')
                var = tk.StringVar(value=value)
                entry = tkb.Entry(config_frame, textvariable=var)
                entry.grid(row=row, column=1, padx=5, pady=2, sticky='ew')
                self.config_vars[f"{section}/{key}"] = var
                row += 1
        
        tkb.Button(config_frame, text="Save Configuration", command=self.save_config, bootstyle=(SUCCESS, OUTLINE)).grid(row=row, column=0, columnspan=2, pady=10)
        
        read_frame = ttk.Labelframe(parent, text="Data Acquisition", padding=10)
        read_frame.grid(row=1, column=0, columnspan=3, padx=5, pady=10, sticky='ew')
        tkb.Button(read_frame, text="DT Read (Single Plot)", command=self.dt_read_mode, bootstyle=SUCCESS).pack(side=LEFT, padx=5, expand=True, fill='x')
        self.ct_button = tkb.Button(read_frame, text="CT Read (Continuous)", command=self.toggle_ct_read, bootstyle=SUCCESS)
        self.ct_button.pack(side=LEFT, padx=5, expand=True, fill='x')

        direct_frame = ttk.Labelframe(parent, text="Direct 32-bit SPI Command", padding=10)
        direct_frame.grid(row=2, column=0, columnspan=3, padx=5, pady=10, sticky='ew')
        direct_frame.columnconfigure(0, weight=1)
        self.entry_spi_direct = tkb.Entry(direct_frame, font=("Consolas", 10))
        self.entry_spi_direct.grid(row=0, column=0, padx=5, pady=5, sticky='ew')
        tkb.Button(direct_frame, text="Send Direct", command=self.send_direct_spi, bootstyle=PRIMARY).grid(row=0, column=1, padx=5, pady=5)

        globals_frame = ttk.Labelframe(parent, text="Global Commands", padding=10)
        globals_frame.grid(row=3, column=0, columnspan=3, padx=5, pady=10, sticky='ew') 
        global_buttons = [("Analog Reset","00011100000000000000000000000000"),("Analog Remove Reset","00100000000000000000000000000000"),("Global DAC On","00100100000000000000000000000000"),("Global DAC Off","00110100000000000000000000000000"),("SET CBOK LOW","01001000000000000000000000000000"),("Dummy","00000000000000000000000000000000")]
        for i, (text, cmd) in enumerate(global_buttons):
            btn = tkb.Button(globals_frame, text=text, command=lambda c=cmd: self.single_tcp(c), bootstyle=SECONDARY)
            btn.grid(row=i//2, column=i%2, padx=5, pady=5, sticky='ew')
        
        tkb.Button(parent, text="Clear Console", command=self.clear_console_output, bootstyle=DANGER).grid(row=4, column=0, columnspan=3, pady=20)

    def create_sequences_tab(self, parent):
        parent.columnconfigure(0, weight=1)
        
        sequence_frame = ttk.Labelframe(parent, text="Select and Run Sequence", padding=10)
        sequence_frame.grid(row=0, column=0, padx=5, pady=10, sticky='ew')
        sequence_frame.columnconfigure(0, weight=1)
        ttk.Label(sequence_frame, text="Available Sequences:").grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky='w')
        self.sequence_map = {"REC_ELE16":self.rec_ele16,"Stim_ELE1":lambda:self.stim_sequence('ELE1'),"Stim_ELE2":lambda:self.stim_sequence('ELE2'),"Stim_ELE5":lambda:self.stim_sequence('ELE5'),"Stim_ELE6":lambda:self.stim_sequence('ELE6'),"Stim_ELE11":lambda:self.stim_sequence('ELE11'),"Stim_ELE12":lambda:self.stim_sequence('ELE12'),"Stim_ELE13":lambda:self.stim_sequence('ELE13'),"Stim_ELE14":lambda:self.stim_sequence('ELE14'),"Stim_ELE16":lambda:self.stim_sequence('ELE16'),"STIM + REC":self.stim_and_rec}
        self.sequence_var = tk.StringVar()
        sequence_dropdown = ttk.Combobox(sequence_frame, textvariable=self.sequence_var, values=list(self.sequence_map.keys()), state='readonly')
        sequence_dropdown.grid(row=1, column=0, padx=5, pady=10, sticky='ew')
        if list(self.sequence_map.keys()):
            sequence_dropdown.current(0)
        tkb.Button(sequence_frame, text="Run", command=self.run_selected_sequence, bootstyle=SUCCESS).grid(row=1, column=1, padx=5, pady=10, sticky='e')

        commands_frame = ttk.Labelframe(parent, text="Common Commands", padding=10)
        commands_frame.grid(row=1, column=0, padx=5, pady=10, sticky='ew')
        tkb.Button(commands_frame, text="Set Gain High", command=self.set_gain_high, bootstyle=SECONDARY).pack(side=LEFT, expand=True, padx=5, fill='x')
        tkb.Button(commands_frame, text="Set Gain Low", command=self.set_gain_low, bootstyle=SECONDARY).pack(side=LEFT, expand=True, padx=5, fill='x')

        stim_frame = ttk.Labelframe(parent, text="Stimulator Parameter Configuration", padding=10)
        stim_frame.grid(row=2, column=0, padx=5, pady=10, sticky='ew')
        stim_frame.columnconfigure((1, 3), weight=1)
        ttk.Label(stim_frame, text="Block (8-bit):").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        tkb.Entry(stim_frame, textvariable=self.stim_block_var).grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        ttk.Label(stim_frame, text="Addr Channel:").grid(row=0, column=2, padx=5, pady=5, sticky='w')
        ttk.Combobox(stim_frame, textvariable=self.stim_addr_channel_var, values=['00', '01', '10', '11'], state='readonly').grid(row=0, column=3, padx=5, pady=5, sticky='ew')
        ttk.Separator(stim_frame, orient=HORIZONTAL).grid(row=1, column=0, columnspan=4, sticky='ew', pady=10)
        ttk.Label(stim_frame, text="Amplitude (9-bit):").grid(row=2, column=0, padx=5, pady=5, sticky='w')
        tkb.Entry(stim_frame, textvariable=self.stim_amplitude_var).grid(row=2, column=1, columnspan=3, padx=5, pady=5, sticky='ew')
        ttk.Label(stim_frame, text="Polarity:").grid(row=3, column=0, padx=5, pady=5, sticky='w')
        ttk.Combobox(stim_frame, textvariable=self.stim_polarity_var, values=['00 (Output 0)', '01 (Negative)', '10 (Positive)', '11 (None)'], state='readonly').grid(row=3, column=1, padx=5, pady=5, sticky='ew')
        ttk.Label(stim_frame, text="DAC Channel:").grid(row=3, column=2, padx=5, pady=5, sticky='w')
        ttk.Combobox(stim_frame, textvariable=self.stim_dac_channel_var, values=['00', '01', '10', '11'], state='readonly').grid(row=3, column=3, padx=5, pady=5, sticky='ew')
        ttk.Label(stim_frame, text="Compensate State:").grid(row=4, column=0, padx=5, pady=5, sticky='w')
        ttk.Combobox(stim_frame, textvariable=self.stim_compensate_var, values=['1 (Enable)', '0 (Disable)'], state='readonly').grid(row=4, column=1, padx=5, pady=5, sticky='ew')
        ttk.Label(stim_frame, text="Amplitude Step:").grid(row=4, column=2, padx=5, pady=5, sticky='w')
        ttk.Combobox(stim_frame, textvariable=self.stim_step_var, values=['1 (200nA)', '0 (4nA)'], state='readonly').grid(row=4, column=3, padx=5, pady=5, sticky='ew')
        ttk.Separator(stim_frame, orient=HORIZONTAL).grid(row=5, column=0, columnspan=4, sticky='ew', pady=10)
        button_frame = ttk.Frame(stim_frame)
        button_frame.grid(row=6, column=0, columnspan=4, sticky='ew')
        tkb.Button(button_frame, text="输出 (Output)", command=self._send_stimulator_output, bootstyle=(SUCCESS, OUTLINE)).pack(side=LEFT, expand=True, padx=5, fill='x')
        tkb.Button(button_frame, text="关闭 (Close)", command=self._send_stimulator_close, bootstyle=(DANGER, OUTLINE)).pack(side=LEFT, expand=True, padx=5, fill='x')

    def create_analysis_tab(self, parent):
        parent.columnconfigure(0, weight=1)
        plot_frame = ttk.Labelframe(parent, text="Analysis Scripts", padding=10)
        plot_frame.grid(row=0, column=0, columnspan=3, padx=5, pady=10, sticky='ew')
        top_row_frame = ttk.Frame(plot_frame)
        top_row_frame.pack(fill='x', expand=True, pady=2)
        bottom_row_frame = ttk.Frame(plot_frame)
        bottom_row_frame.pack(fill='x', expand=True, pady=2)
        tkb.Button(top_row_frame, text="Plot Multi-Channel", command=self.rec_muti, bootstyle=INFO).pack(side=LEFT, padx=5, expand=True, fill='x')
        tkb.Button(top_row_frame, text="Plot Single Spectrum", command=self.rec_single, bootstyle=INFO).pack(side=LEFT, padx=5, expand=True, fill='x')
        tkb.Button(bottom_row_frame, text="Plot Single Channel RT", command=self.plot_single_channel_rt, bootstyle=PRIMARY).pack(side=LEFT, padx=5, expand=True, fill='x')
        tkb.Button(bottom_row_frame, text="Plot Single Channel RT FFT", command=self.plot_single_channel_rt_fft, bootstyle=PRIMARY).pack(side=LEFT, padx=5, expand=True, fill='x')
    
    def save_config(self):
        new_config_dict = {}
        for key, var in self.config_vars.items():
            section, option = key.split('/')
            if section not in new_config_dict:
                new_config_dict[section] = {}
            new_config_dict[section][option] = var.get()
        
        new_config_dict['Stimulator'] = {
            'block': self.stim_block_var.get(),
            'addr_channel': self.stim_addr_channel_var.get(),
            'amplitude': self.stim_amplitude_var.get(),
            'polarity': self.stim_polarity_var.get(),
            'compensate': self.stim_compensate_var.get(),
            'step': self.stim_step_var.get(),
            'dac_channel': self.stim_dac_channel_var.get()
        }
        
        try:
            self.config_manager.save(new_config_dict)
            self.app_config = self.config_manager.load() 
            self.load_attributes_from_config()
            messagebox.showinfo("Success", "Configuration saved and reloaded successfully.")
        except Exception as e:
            self.log(f"Error saving config: {e}", 'error')
            messagebox.showerror("Error", f"Could not save configuration file.\n{e}")
            
    def dt_read_mode(self):
        self.log("Starting DT Read...")
        NUM_LOOPS = 15
        POINTS_PER_CHUNK = self.SIZE_TCPIP_SEND_BUF_TRUNK // 4
        points_total_to_receive = NUM_LOOPS * POINTS_PER_CHUNK
        voltage_data = np.zeros(points_total_to_receive)
        self.log(f"Hardware constraint: Reading exactly {points_total_to_receive} points ({NUM_LOOPS} chunks)...")

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5.0)
                s.connect((self.HOST, self.PORT))
                s.sendall(b'read')
                self.log("Connection successful. Receiving data...")
                loop_count = 0
                while loop_count < NUM_LOOPS:
                    bytes_chunk = self.recieve_tcpip(s, POINTS_PER_CHUNK * 4)
                    if not bytes_chunk:
                        self.log(f"Data stream ended unexpectedly after {loop_count} chunks.", 'warning')
                        break
                    values = np.frombuffer(bytes_chunk, dtype='<u4')
                    voltage_chunk = values / 4096.0 * 1.8
                    start_idx = loop_count * POINTS_PER_CHUNK
                    end_idx = start_idx + POINTS_PER_CHUNK
                    voltage_data[start_idx:end_idx] = voltage_chunk
                    loop_count += 1
            
            voltage_data = voltage_data[:loop_count * POINTS_PER_CHUNK]
            if voltage_data.size == 0:
                self.log("Failed to receive any data.", 'error')
                return
            
            self.log(f"Data received ({voltage_data.size} points). Plotting...")
            if self.FFT_POINTS > voltage_data.size:
                self.log(f"Warning: FFT points in config ({self.FFT_POINTS}) is larger than "
                         f"received data ({voltage_data.size}). Analysis might use truncated data.", 'warning')

            plt.ion()
            fig, ax = plt.subplots(figsize=(10, 6))
            time_axis = np.arange(len(voltage_data)) / self.FS
            ax.plot(time_axis, voltage_data)
            ax.set_title("Single Data Acquisition (DT Read)")
            ax.set_xlabel("Time (s)")
            ax.set_ylabel("Voltage (V)")
            ax.grid(True)
            plt.pause(0.001)

        except socket.timeout:
            self.log("CRITICAL ERROR: Connection timed out.", 'error')
        except Exception as e:
            self.log(f"CRITICAL ERROR: An exception occurred: {e}", 'error')

    def toggle_ct_read(self):
        if self.is_streaming:
            self.stop_ct_read()
        else:
            self.start_ct_read()

    def start_ct_read(self):
        self.log("Starting CT Read...")
        NUM_LOOPS = 15
        POINTS_PER_CHUNK = self.SIZE_TCPIP_SEND_BUF_TRUNK // 4
        points_total = NUM_LOOPS * POINTS_PER_CHUNK
        voltage_buffer = np.zeros(points_total)
        
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5.0)
                s.connect((self.HOST, self.PORT))
                s.sendall(b'read')
                self.log("Connection successful. Receiving full data buffer for CT mode...")
                chunks_received = 0
                for i in range(NUM_LOOPS):
                    bytes_chunk = self.recieve_tcpip(s, POINTS_PER_CHUNK * 4)
                    if not bytes_chunk:
                        self.log(f"Data stream ended after {i} chunks.", 'warning')
                        break
                    values = np.frombuffer(bytes_chunk, dtype='<u4')
                    voltage_buffer[i*POINTS_PER_CHUNK:(i+1)*POINTS_PER_CHUNK] = values / 4096.0 * 1.8
                    chunks_received += 1
            
            self.ct_voltage_buffer = voltage_buffer[:chunks_received * POINTS_PER_CHUNK]
        except Exception as e:
            self.log(f"Failed to pre-fetch data for CT Read: {e}", 'error')
            return

        if self.ct_voltage_buffer.size == 0:
            self.log("No data received for CT mode.", 'error')
            return

        self.log("Full data buffer received. Starting animation...")
        self.is_streaming = True
        self.ct_button.config(text="Stop CT Read", bootstyle=DANGER)

        self.fig, self.ax = plt.subplots(figsize=(10, 6))
        self.fig.canvas.mpl_connect('close_event', self._on_ct_plot_close)
        self.ax.set_title("Continuous Data Stream (CT Read from Buffer)")
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Voltage (V)")
        self.ax.grid(True)
        ymin, ymax = self.ct_voltage_buffer.min(), self.ct_voltage_buffer.max()
        margin = (ymax - ymin) * 0.1
        self.ax.set_ylim(ymin - margin, ymax + margin)
        self.num_display_points = 4096
        self.time_axis_segment = np.arange(self.num_display_points) / self.FS
        self.line, = self.ax.plot(self.time_axis_segment, np.zeros(self.num_display_points), lw=1)
        self.ax.set_xlim(0, self.time_axis_segment[-1])
        frame_count = len(self.ct_voltage_buffer) // self.num_display_points
        self.ani = FuncAnimation(self.fig, self.update_plot, frames=frame_count, interval=100, blit=True)
        plt.show(block=False)

    def update_plot(self, frame):
        try:
            start_index = frame * self.num_display_points
            end_index = start_index + self.num_display_points
            data_segment = self.ct_voltage_buffer[start_index:end_index]
            self.line.set_ydata(data_segment)
        except Exception as e:
            self.log(f"Error during plot update: {e}", 'error')
        return self.line,

    def _on_ct_plot_close(self, event):
        self.log("CT plot window closed by user, stopping animation.")
        if self.ani:
            self.ani.event_source.stop()
            self.ani = None
        self.is_streaming = False
        self.fig = None
        self.ct_button.config(text="CT Read (Continuous)", bootstyle=SUCCESS)

    def stop_ct_read(self):
        if self.fig:
            plt.close(self.fig) # This will trigger _on_ct_plot_close
        else: # If fig is already gone, manually clean up
            self._on_ct_plot_close(None)
        self.log("CT Read stopped by button.")

    def on_closing(self):
        if self.is_streaming:
            self.stop_ct_read()
        self.destroy()
    
    def log(self, message, style=''):
        if hasattr(self, 'console_output') and self.console_output:
            self.console_output.insert(tk.END, message + "\n")
            self.console_output.see(tk.END)

    def clear_console_output(self):
        self.console_output.delete(1.0, tk.END)

    def recieve_tcpip(self, conn, num_to_recieve, max_attemp=-1):
        data = bytearray()
        conn.setblocking(False)
        start_time = time.time()
        while num_to_recieve > 0:
            try:
                rx_data = conn.recv(min(num_to_recieve, self.SIZE_TCPIP_SEND_BUF_TRUNK))
                if rx_data:
                    data.extend(rx_data)
                    num_to_recieve -= len(rx_data)
                    start_time = time.time()
                else:
                    self.log("Connection closed by peer during receive.", 'warning')
                    break
            except BlockingIOError:
                time.sleep(0.01)
                if max_attemp != -1 and (time.time() - start_time) > max_attemp:
                    self.log("Receive timeout.", 'warning')
                    break
                continue
            except Exception as e:
                self.log(f"Receive Error: {e}", 'error')
                break
        return data

    def single_tcp(self, spi_cmd, show_reply=True):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5.0)
                s.connect((self.HOST, self.PORT))
                spi_cmd_clean = spi_cmd.replace("_","").replace(" ","")
                binary_data = bytearray(int(spi_cmd_clean[i:i+8],2) for i in range(0,len(spi_cmd_clean),8))
                hex_data = binascii.hexlify(binary_data).decode()
                message = "spi" + hex_data
                self.log(f"Sending: {message}")
                self.log(f"  > Code: {spi_cmd_clean[0:6]}, Addr: {spi_cmd_clean[6:16]}, Data: {spi_cmd_clean[16:32]}")
                s.sendall(message.encode())
                if not show_reply:
                    return
                data = self.recieve_tcpip(s, 12, max_attemp=5)
                if not data:
                    self.log("No reply received.", 'error')
                    return
                for i in range(8, len(data), 4):
                    show_data = data[i:i+4]
                    hex_reply = binascii.hexlify(show_data).decode()
                    hex_reply = "".join(reversed([hex_reply[i:i+2] for i in range(0,len(hex_reply),2)]))
                    bin_reply = bin(int(hex_reply, 16))[2:].zfill(32)
                    log_msg = f"Received: Code: {bin_reply[0:6]}, Addr: {bin_reply[6:16]}, Data: {bin_reply[16:32]}"
                    if bin_reply[0:6] == '010011':
                        adc_val = int(bin_reply[20:32],2)
                        voltage = adc_val / 4095.0 * 1.8
                        log_msg += f", Value: {voltage:.4f}V"
                    self.log(log_msg,'success')
        except Exception as e:
            self.log(f"Connection Error: {e}",'error')

    def send_direct_spi(self):
        raw_cmd = self.entry_spi_direct.get()
        cleaned_cmd = raw_cmd.strip().replace("_", "").replace(" ", "")
        if len(cleaned_cmd) != 32:
            error_msg = f"Error: Direct command must be 32 bits, but got {len(cleaned_cmd)}."
            self.log(error_msg, 'error')
            messagebox.showerror("Invalid Length", error_msg)
            return
        if not all(c in '01' for c in cleaned_cmd):
            error_msg = "Error: Direct command contains invalid characters. Only '0' and '1' are allowed."
            self.log(error_msg, 'error')
            messagebox.showerror("Invalid Characters", error_msg)
            return
        self.single_tcp(cleaned_cmd)

    def run_script(self, script_name):
        try:
            self.log(f"Running script: {script_name}...")
            script_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), script_name)
            if not os.path.exists(script_path):
                self.log(f"Error: Script '{script_name}' not found in {os.path.dirname(script_path)}.", 'error')
                return
            subprocess.run(["python", script_path], check=True, text=True, capture_output=True)
            self.log(f"Finished running {script_name}.")
        except FileNotFoundError:
            self.log(f"Error: 'python' command not found. Is Python in your system's PATH?", 'error')
        except subprocess.CalledProcessError as e:
            self.log(f"Error running script {script_name}. Return code: {e.returncode}", 'error')
            self.log(f"--- Script STDOUT ---\n{e.stdout}\n--- Script STDERR ---\n{e.stderr}", 'error')
        except Exception as e:
            self.log(f"An unexpected error occurred while running script: {e}", 'error')

    def rec_muti(self):
        self.run_script("plot_multichannel.py")
    
    def rec_single(self):
        self.run_script("plot_spectrum_single.py")

    def plot_single_channel_rt(self):
        self.run_script("plot_singlechannel_fft.py")

    def plot_single_channel_rt_fft(self):
        self.run_script("plot_singlechanel_rt_fft.py")

    def run_selected_sequence(self):
        selected = self.sequence_var.get()
        if selected and selected in self.sequence_map:
            self.log(f"--- Running Sequence: {selected} ---")
            action = self.sequence_map[selected]
            action()
            self.log(f"--- Sequence {selected} Finished ---")
        else:
            self.log("No sequence selected or invalid sequence.", 'error')

    def rec_ele16(self):
        self.log("Configuring block 48 for electrode...")
        self.single_tcp("0"*32,show_reply=False); time.sleep(0.1)
        self.single_tcp("01000000110000001110100000000001"); time.sleep(0.1)
        self.log("Reading back electrode config...")
        self.single_tcp("0"*32,show_reply=False); time.sleep(0.1)
        self.single_tcp("01000100110000000000000000000000"); time.sleep(0.1)
        self.log("Removing analog global reset...")
        self.single_tcp("0"*32,show_reply=False); time.sleep(0.1)
        self.single_tcp("00100000000000000000000000000000")

    def stim_sequence(self, electrode_key):
        params = {'ELE1':("0011100001","0111100111111110","0111000111111110","0011100001","0111001011111111"),'ELE2':("0011100001","0101100111111110","0101000111111110","0011100001","0101001011111111"),'ELE11':("0011000001","0011100111111110","0011000111111110","0011000001","0011001011111111"),'ELE12':("0011000001","0001100111111110","0001000111111110","0011000001","0001001011111111"),'ELE13':("0011000000","0111100111111110","0111000111111110","0011000000","0111001011111111"),'ELE14':("0011000000","0101100111111110","0101000111111110","0011000000","0101001011111111"),'ELE16':("0011000000","0001100111111110","0001000111111110","0011000000","0001001011111111"),'ELE5':("0011100000","0111100111111110","0111000111111110","0011100000","0111010111111111"),'ELE6':("0011100000","0101100111111110","0101000111111110","0011100000","0101010111111111")}
        if electrode_key not in params:
            self.log(f"Unknown electrode key: {electrode_key}",'error')
            return
        addr, comp_on, comp_off, cbok_addr, stim_data = params[electrode_key]
        self.log("Step 1: Dummy Write"); self.single_tcp("0"*32, show_reply=False); time.sleep(0.1)
        self.log("Step 2: Compensation ON"); self.single_tcp(f"000110{addr}{comp_on}"); time.sleep(0.1)
        self.log("Step 3: Compensation OFF"); self.single_tcp(f"000110{addr}{comp_off}"); time.sleep(0.1)
        self.log("Step 4: Read CBOK"); self.single_tcp(f"000011{addr}{'0'*16}"); time.sleep(0.1)
        self.log("Step 5: Set CBOK LOW"); self.single_tcp(f"010010{cbok_addr}{'0'*16}"); time.sleep(0.1)
        self.log("Step 6: Stimulate"); self.single_tcp(f"000110{addr}{stim_data}"); time.sleep(0.1)

    def stim_and_rec(self):
        self.stim_sequence('ELE16')
        self.log("Stimulation finished, starting DT_Read...")
        self.dt_read_mode()

    def set_gain_high(self):
        self.log("Setting global gain to HIGH...")
        # TODO: 请将 "000..." 替换为实际的32位 Set Gain High SPI 命令
        spi_cmd = "00110100000000000000000000000001" # 这是一个示例，请务必修改
        self.single_tcp(spi_cmd)

    def set_gain_low(self):
        self.log("Setting global gain to LOW...")
        # TODO: 请将 "000..." 替换为实际的32位 Set Gain Low SPI 命令
        spi_cmd = "00110100000000000000000000000000" # 这是一个示例，请务必修改
        self.single_tcp(spi_cmd)

    def _assemble_stimulator_command(self, off_stim_bit):
        try:
            cmd_prefix = "000110"
            block_val = self.stim_block_var.get().zfill(8)
            addr_channel_val = self.stim_addr_channel_var.get().split(' ')[0]
            address = block_val + addr_channel_val
            dac_channel_val = self.stim_dac_channel_var.get().split(' ')[0]
            step_val = self.stim_step_var.get().split(' ')[0]
            compensate_val = self.stim_compensate_var.get().split(' ')[0]
            polarity_val = self.stim_polarity_var.get().split(' ')[0]
            amplitude_val = self.stim_amplitude_var.get().zfill(9)
            data_field = (off_stim_bit + dac_channel_val + step_val + compensate_val + polarity_val + amplitude_val)
            full_cmd = cmd_prefix + address + data_field
            if len(full_cmd) != 32:
                self.log(f"Error: Assembled command length is not 32 bits! It is {len(full_cmd)}", 'error')
                return None
            return full_cmd
        except Exception as e:
            self.log(f"Error assembling command: {e}", 'error')
            return None

    def _send_stimulator_output(self):
        self.log("Sending Stimulator 'Output' command...")
        spi_cmd = self._assemble_stimulator_command(off_stim_bit='0')
        if spi_cmd:
            #dummy
            self.single_tcp("0"*32, show_reply=False); time.sleep(0.1)
            self.single_tcp(spi_cmd)

    def _send_stimulator_close(self):
        self.log("Sending Stimulator 'Close' command...")
        spi_cmd = self._assemble_stimulator_command(off_stim_bit='1')
        if spi_cmd:
            #dummy
            self.single_tcp("0"*32, show_reply=False); time.sleep(0.1)
            self.single_tcp(spi_cmd)

if __name__ == "__main__":
    app = NeuralinkTesterApp()
    app.mainloop()