import socket
import socketserver
import time
import struct
import numpy as np
import binascii

HOST, PORT = "localhost", 7

class DeviceTCPHandler(socketserver.BaseRequestHandler):
    def handle(self):
        print(f"[*] Accepted connection from: {self.client_address[0]}")
        try:
            command_data = self.request.recv(1024).strip().decode('utf-8')
            if not command_data:
                print("[-] Client disconnected without sending a command.")
                return

            print(f"[<] Received command: {command_data[:50]}...")

            if command_data.startswith("spi"):
                hex_data = command_data[3:]
                print(f"  > Parsed SPI hex data: {hex_data}")
                response = bytearray(b'\xDE\xAD\xBE\xEF\x00\x00\x00\x00') 
                try:
                    incoming_cmd_bytes = binascii.unhexlify(hex_data)
                    binary_str = bin(int(hex_data, 16))[2:].zfill(64) # Assume 64-bit for safety
                    code = binary_str[:6]
                    if code == '010011':
                        simulated_adc_value = 2048
                        sim_data_part = format(simulated_adc_value, '012b')
                        reply_binary = binary_str[:16] + "0000" + sim_data_part
                        reply_int = int(reply_binary, 2)
                        response.extend(struct.pack('<I', reply_int))
                    else:
                        response.extend(incoming_cmd_bytes[:4]) # Echo first 4 bytes
                    self.request.sendall(response)
                    print(f"[>] Sent SPI response: {binascii.hexlify(response).decode()}")
                except Exception as e:
                    print(f"[!] Error processing SPI command: {e}")

            elif command_data.startswith("set"):
                hex_data = command_data[3:]
                print(f"  > Set mode/channel to data: {hex_data}")
                print("[>] Acknowledged 'set' command.")

            elif command_data.startswith("read") or command_data.startswith("ctread"):
                print("  > Data read command received. Starting stream...")
                self.stream_simulated_data()
            else:
                print(f"[!] Unknown command received: {command_data}")

        except Exception as e:
            print(f"[-] An error occurred with client {self.client_address[0]}: {e}")
        finally:
            print(f"[*] Connection with {self.client_address[0]} closed.")

    def stream_simulated_data(self):
        num_points_per_chunk = 1024
        amplitude = 500
        offset = 2048
        frequency = 1
        noise_level = 20
        phase = 0
        
        while True:
            try:
                t = np.linspace(phase, phase + 2 * np.pi * frequency, num_points_per_chunk, endpoint=False)
                sine_wave = amplitude * np.sin(t) + offset
                noise = np.random.normal(0, noise_level, num_points_per_chunk)
                simulated_data = (sine_wave + noise).astype(np.uint32)
                simulated_data = np.clip(simulated_data, 0, 4095)
                
                data_chunk = simulated_data.tobytes()
                self.request.sendall(data_chunk)
                phase = t[-1] + (t[1] - t[0])
                time.sleep(0.02)
            except (BrokenPipeError, ConnectionResetError):
                print("[!] Client disconnected during data stream. Stopping.")
                break
            except Exception as e:
                print(f"[-] Error during data stream: {e}")
                break

if __name__ == "__main__":
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer((HOST, PORT), DeviceTCPHandler) as server:
        print(f"[*] Dummy server listening on {HOST}:{PORT}...")
        print("[*] Ready to accept connections from the GUI.")
        print("[*] Press Ctrl+C to shut down.")
        server.serve_forever()