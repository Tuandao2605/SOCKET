import tkinter as tk
from tkinter import filedialog, messagebox
import socket
import os
from datetime import datetime
HOST = "127.0.0.1"
PORT = 65432
FORMAT = "utf8"
UPLOAD_FOLDER = "client_uploads"
DOWNLOAD_FOLDER = "client_downloads"

# Tạo thư mục lưu trữ nếu chưa tồn tại
# if not os.path.exists(UPLOAD_FOLDER):
#     os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

def upload_file(client, filepath):
    if not os.path.isabs(filepath):  # Nếu không phải đường dẫn tuyệt đối
        filepath = os.path.join(UPLOAD_FOLDER, filepath)  # Thêm thư mục mặc định

    if not os.path.exists(filepath):
        print(f"Filepath '{filepath}' không tồn tại. ")
        client.sendall('1'.encode(FORMAT))  # Gửi thông báo File không tồn tại
        return
    
    try:
        filename = os.path.basename(filepath)  # Lấy tên file từ đường dẫn
        client.sendall(f"upload {filename}".encode(FORMAT))
        response = client.recv(1024).decode(FORMAT)
        if response != "READY":
            print("Server không sẵn sàng nhận file.")
            return

        file_size = os.path.getsize(filepath)
        client.sendall(str(file_size).encode(FORMAT))
        response = client.recv(1024).decode(FORMAT)
        if response != "SIZE_RECEIVED":
            print("Server không nhận được kích thước file.")
            return

        with open(filepath, "rb") as f:
            sent = 0
            while True:
                data = f.read(1024)
                if not data:
                    break
                client.sendall(data)

                # Công thức tính tiến độ %
                sent += len(data)
                progress = (sent / file_size) * 100

                print(f"Đang gửi file: {progress:.2f}%", end="\r")

        print(f"\nFile '{filename}' đã tải lên thành công.")
        
    except Exception as e:
        print(f"Lỗi khi tải lên file: {e}")

    finally:
        # Sau khi upload thì đóng Client tránh rò rỉ tài nguyên
        client.close()
        exit()


def get_unique_filename(folder, filename):
    """Kiểm tra và trả về tên file không trùng."""
    filepath = os.path.join(folder, filename)
    while os.path.exists(filepath):
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        name, ext = os.path.splitext(filename)
        filename = f"{name}_{timestamp}{ext}"
        filepath = os.path.join(folder, filename)
    return filepath


def download_file(client, filepath):   
    # Chỉ lấy tên File để lưu 
    if not os.path.isabs(filepath):
        filename = filepath  
    else: 
        filename = os.path.basename(filepath)

    try:
        # Lấy đường dẫn và tên File
        filepath = get_unique_filename(DOWNLOAD_FOLDER, filename) 
        print(f"File sẽ được lưu tại: {filepath}")
        filename = os.path.basename(filepath)

        response = client.recv(1024).decode(FORMAT)
        if response.startswith("SIZE"):
            file_size = int(response.split(" ")[1]) # Kích thước File cần download
            client.sendall("READY".encode(FORMAT))

            with open(filepath, "wb") as f:
                received = 0
                while received < file_size:
                    data = client.recv(1024)
                    if not data:
                        break
                    f.write(data)
                    received += len(data)
                    progress = (received / file_size) * 100
                    print(f"Đang nhận file: {progress:.2f}%", end="\r")

            print(f"\nFile '{filename}' đã tải xuống thành công.")
        else:
            print(response)

    except Exception as e:
        print(f"Lỗi khi tải file: {e}")

    finally:
        # Sau khi download thì đóng Client tránh rò rỉ tài nguyên
        client.close()
        exit()

# Tạo một socket TCP/IP dựa trên IPv4
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
print("\tCLIENT\n")

try:
    # Kết nối đến server
    client.connect((HOST, PORT))
    print("Client", client.getsockname())
    
    # Nhận thông điệp đầu tiên từ server (yêu cầu nhập mã PIN)
    msg = client.recv(1024).decode(FORMAT)
    print(msg)

    # Nhập mã PIN từ người dùng
    pin = input("Enter PIN: ")
    
    # Gửi mã PIN cho server
    client.sendall(pin.encode(FORMAT))

    # Nhận phản hồi từ server (xác nhận mã PIN)
    response = client.recv(1024).decode(FORMAT)
    print(response)

    # Nếu mã PIN sai, đóng kết nối và thoát ngay
    if response == "Connection failed.\n ":
        print("Invalid PIN. Exiting...")
        client.close()
        exit()

        # Yêu cầu đăng nhập tài khoản/mật khẩu
    while True:
        msg = client.recv(1024).decode(FORMAT)
        print(msg)
        username = input("Username: ")
        client.sendall(username.encode(FORMAT))
        msg = client.recv(1024).decode(FORMAT)
        print(msg)
        password = input("Password: ")
        client.sendall(password.encode(FORMAT))
    
        login_response = client.recv(1024).decode(FORMAT)
        print(login_response)
        if login_response.startswith("Welcome"):
            break  # Đăng nhập thành công, thoát khỏi vòng lặp
        else:
            print("Invalid username or password.")

    msg = None
    while (msg!= 'x'):
        msg = input(">> ")
        client.sendall(msg.encode(FORMAT))
        if msg == 'x':  # Kiểm tra nếu người dùng nhập 'x'
            print("Disconnecting...")
            break  # Thoát vòng lặp

        if msg.startswith("upload "):                
            filepath = msg.split(" ")[1]
            upload_file(client, filepath)
        elif msg.startswith("download "):
            filepath = msg.split(" ")[1]
            download_file(client, filepath)
       
        msg = client.recv(1024).decode(FORMAT)
        print("Server response: " , msg)

except socket.error:
    print("ERROR")       

finally:
    client.close()


