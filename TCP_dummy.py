import socket

def main():
    HOST = '127.0.0.1'
    PORT = 12345

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind((HOST, PORT))
        server_socket.listen(1)
        print('等待连接...')
        conn, addr = server_socket.accept()
        with conn:
            print('连接已建立：', addr)
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                print('收到消息:', data.decode())
                conn.sendall('消息已收到'.encode())  # 将字符串编码为字节对象再发送

if __name__ == "__main__":
    main()
