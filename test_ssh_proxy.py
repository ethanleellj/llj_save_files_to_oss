import socket
import paramiko
import sys

proxy_host = "127.0.0.1"
proxy_port = 18080
target_host = "8.219.145.76"
target_port = 22
username = "ethan"
key_path = "/workspace/ssh_key"

try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((proxy_host, proxy_port))
    
    connect_req = f"CONNECT {target_host}:{target_port} HTTP/1.1\r\nHost: {target_host}:{target_port}\r\n\r\n"
    sock.sendall(connect_req.encode())
    
    response = b""
    while b"\r\n\r\n" not in response:
        chunk = sock.recv(4096)
        if not chunk:
            break
        response += chunk
    
    print(f"Proxy response: {response.decode().splitlines()[0]}")
    
    if b"200" not in response.split(b"\r\n")[0]:
        print("Proxy connection failed!")
        sys.exit(1)
    
    print("Proxy tunnel established...")
    
    transport = paramiko.Transport(sock)
    transport.start_client()
    
    print(f"Server host key type: {transport.get_remote_server_key().get_name()}")
    
    try:
        key = paramiko.RSAKey.from_private_key_file(key_path)
        print(f"RSA key loaded successfully, bits: {key.get_bits()}")
        transport.auth_publickey(username, key)
        print("RSA auth success!")
    except paramiko.AuthenticationException as e:
        print(f"RSA auth failed: {e}")
        try:
            transport2 = paramiko.Transport(socket.socket(socket.AF_INET, socket.SOCK_STREAM))
            sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock2.connect((proxy_host, proxy_port))
            connect_req2 = f"CONNECT {target_host}:{target_port} HTTP/1.1\r\nHost: {target_host}:{target_port}\r\n\r\n"
            sock2.sendall(connect_req2.encode())
            resp2 = b""
            while b"\r\n\r\n" not in resp2:
                chunk = sock2.recv(4096)
                if not chunk:
                    break
                resp2 += chunk
            transport2 = paramiko.Transport(sock2)
            transport2.start_client()
            
            print("Trying interactive auth...")
            try:
                transport2.auth_interactive(username, lambda title, instructions, fields: ["ethan123"])
                print("Password auth success!")
            except Exception as e3:
                print(f"Password auth failed: {e3}")
            transport2.close()
            sock2.close()
        except Exception as e2:
            print(f"Password auth error: {e2}")
    
    if transport.is_authenticated():
        print("SSH连接成功！")
        chan = transport.open_session()
        chan.exec_command("whoami; uname -a; id")
        print(chan.recv(4096).decode())
        chan.close()
    
    transport.close()
    sock.close()
    
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
