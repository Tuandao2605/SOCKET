import socket
import threading
import os
from datetime import datetime

# Địa chỉ loopback
HOST = "127.0.0.1" 
PORT = 65432
FORMAT = "utf8"

# Mã pin để client xác nhận
SERVER_PIN = "1234" 
#Thư mục để server lưu trữ File
UPLOAD = "Upload"
DOWNLOAD = "Download"

# Tao thu muc luu tru neu chua ton tai
if not os.path.exists(UPLOAD):
    os.makedirs(UPLOAD)
# if not os.path.exists(DOWNLOAD):
#     os.makedirs(DOWNLOAD)
def validate_login(username, password):
    # Cơ sở dữ liệu người dùng đơn giản (username và password)
    user_database = {
        "user1": "password1",
        "user2": "password2",
        "admin": "admin123",
    }
    return user_database.get(username) == password


def handle_upload(conn, filename):
    if os.path.isabs(filename): # Nếu filename là đường dẫn
        filename = os.path.basename(filename)

    filepath = os.path.join(UPLOAD, filename)

    # Đảm bảo tên file duy nhất 
    if os.path.exists(filepath):
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        name, ext = os.path.splitext(filename)
        filename = f"{name}_{timestamp}{ext}"
        filepath = os.path.join(UPLOAD, filename)
    print(f"File sẽ được lưu tại: {filepath}")
    
    try:
        # Nhận phản hồi từ client File có tồn tại hay không
        msg = conn.recv(1024).decode(FORMAT)
        if(msg != '1'):    # Nếu msg == 1 tức là client kiểm tra rằng File muốn upload không tồn tại 
            conn.sendall("READY".encode(FORMAT))
            file_size = int(conn.recv(1024).decode(FORMAT))
            conn.sendall("SIZE_RECEIVED".encode(FORMAT))

            with open(filepath, "wb") as f:
                received = 0
                while received < file_size: # Từng tự nhận data từ client sau đó ghi File
                    data = conn.recv(1024)
                    if not data:
                        break
                    f.write(data)

                    # Công thức tính tiến độ %
                    received += len(data)
                    progress = (received / file_size) * 100 

                    print(f"Receiving file '{filename}': {progress:.2f}%", end="\r")

            print(f"\nFile '{filename}' has been successfully uploaded.")
            conn.sendall(f"File '{filename}' uploaded successfully.".encode(FORMAT))

    except Exception as e:
        print(f"Error uploading file: {e}")
        conn.sendall(f"Error uploading file: {e}".encode(FORMAT))

def handle_download(conn, filename):
    if not os.path.isabs(filename): # Nếu filename không phải là đường dẫn
        filepath = os.path.join(DOWNLOAD, filename)
    else :
        filepath = filename
        filename = os.path.basename(filepath)

    if not os.path.exists(filepath):
        conn.sendall(f"File '{filename}' with path: '{filepath}' does not exist.".encode(FORMAT))
        return

    try:
        file_size = os.path.getsize(filepath)
        conn.sendall(f"SIZE {file_size}".encode(FORMAT)) # Gửi kích thước File cần download cho client
        response = conn.recv(1024).decode(FORMAT)
        if response != "READY":
            return

        with open(filepath, "rb") as f:
            sent = 0
            while True:
                data = f.read(1024)
                if not data:
                    break
                conn.sendall(data)
                sent += len(data)
                progress = (sent / file_size) * 100
                print(f"Sending file '{filename}': {progress:.2f}%", end="\r")
        print(f"\nFile '{filename}' has been successfully sent.")

    except Exception as e:
        print(f"Error sending file: {e}")
        conn.sendall(f"Error sending file: {e}".encode(FORMAT))
    

def handleClient(conn, addr):
    print("Client:", conn.getsockname(), "connected")
    try:
        # Xác thực mã PIN
        conn.sendall("Please enter your PIN: ".encode(FORMAT))
        pin = conn.recv(1024).decode(FORMAT).strip()  # Loại bỏ các ký tự thừa
        # Kiểm tra mã PIN
        if pin == SERVER_PIN:
            conn.sendall("Connection successful!\nWelcome. You are now connected. Type 'x' to disconnect".encode(FORMAT))
            while True:
                # Nhận thông tin đăng nhập (username và password) từ client
                conn.sendall("Please enter your username: ".encode(FORMAT))
                username = conn.recv(1024).decode(FORMAT).strip()  # Nhận username
                print(f"Received username: {username}")
                conn.sendall("Please enter your password: ".encode(FORMAT))
                password = conn.recv(1024).decode(FORMAT).strip()  # Nhận password
                print(f"Received password: {password}") # Debug print
                # Kiểm tra thông tin đăng nhập
                if validate_login(username, password):  # Hàm validate_login sẽ kiểm tra thông tin
                    conn.sendall(f"Welcome {username}! You are now connected. Type 'x' to disconnect.".encode(FORMAT))
                    print(f"Connection successful for username: {username}")
                    break
                else:
                    conn.sendall("Login failed. Invalid username or password.\n".encode(FORMAT))
                    print("Client:", conn.getsockname(), "disconnected due to invalid login.")
        else:
            conn.sendall("Connection failed.\n ".encode(FORMAT))
            print("Client:", conn.getsockname(), "disconnected")
            conn.close()
            return
           
        msg = None
        while msg != 'x':  # Kiểm tra nếu người dùng nhập 'x'
            msg = conn.recv(1024).decode(FORMAT)
            print("Client", addr, ": ", msg)

            if msg == 'x':  # Thoát vòng lặp nếu nhập 'x'
                break

            # Xử lý upload và download
            if msg.startswith("upload "):
                filename = msg.split(" ", 1)[1]
                handle_upload(conn, filename)

            elif msg.startswith("download "):
                filename = msg.split(" ", 1)[1]
                handle_download(conn, filename)

            # Gửi phản hồi từ server
            msg = input("Server response: ")
            conn.sendall(msg.encode(FORMAT))

        print("Client", addr, "finished")
        print(conn.getsockname(), "closed")
    except ConnectionResetError as e:
        print(f"Connection reset by peer: {e}")
        conn.close()
    except Exception as e:
        print(f"Unexpected error: {e}")
        conn.close()
    finally:
        conn.close()

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
print("\tSERVER\n")

server.bind( (HOST, PORT) )
server.listen(5) # Lắng nghe tối đa 5 kết nối client cùng lúc

print("SERVER", HOST, PORT)
print("Waiting for client ")

try:
    while True:
        # conn là socket để server giao tiếp với client sau khi kết nối được thiết lập.
        # addr là thông tin địa chỉ (IP và Port) của client, giúp server biết được nơi client kết nối từ đâu.
        conn, addr = server.accept()
        # Đa luồng
        client_thread = threading.Thread(target = handleClient, args = (conn, addr))

        # Đặt luồng mới là daemon, để nó tự động dừng khi server chính dừng.
        #Các luồng client sẽ tự động dừng khi chương trình chính kết thúc.
        client_thread.daemon = True
        client_thread.start()

except socket.error:
    print("ERROR")


print("END")

server.close()