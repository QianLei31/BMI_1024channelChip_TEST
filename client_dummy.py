import socket

def main():
    HOST = '127.0.0.1'
    PORT = 12345

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
        client_socket.connect((HOST, PORT))
        message = 'Hello, server!'
        client_socket.sendall(message.encode())
        data = client_socket.recv(1024)
        print('收到来自服务器的回复:', data.decode())

if __name__ == "__main__":
    main()
