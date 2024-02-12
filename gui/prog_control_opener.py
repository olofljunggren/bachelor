import paramiko
import os

def ssh_connect(hostname, port, username, password):
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_client.load_system_host_keys()

    try:
        ssh_client.connect(hostname, port, username, password)
        print(f"Connected to {hostname}")
    except Exception as e:
        print(f"Failed to connect to {hostname}: {e}")
        ssh_client = None

    return ssh_client

def open_remote_python_file(ssh_client, remote_file_path):

    try:
        sftp_client = ssh_client.exec_command("python3 " + remote_file_path)
    except Exception as e:
        print(f"Failed to open remote file: {e}")

def main():
    hostname = "192.168.5.3"
    port = 22  # Default SSH port, change if needed
    username = "admin"
    password = "kingkong"
    remote_file_path = "/home/admin/Documents/communcation-module/control.py"

    ssh_client = ssh_connect(hostname, port, username, password)

    if ssh_client:
        open_remote_python_file(ssh_client, remote_file_path)
        ssh_client.close()

if __name__ == "__main__":
    main()
