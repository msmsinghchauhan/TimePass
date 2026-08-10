import paramiko

def get_remote_log(host,username,password,remote_path,local_path):
    # Create ssh client
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=username, password=password)
    sftp=ssh.open_sftp()
    # Download the log file
    sftp.get(remote_path,local_path)
    sftp.close()
    ssh.close()

    if __name__ == "__main__":
        host = "198.168.56.1"
        username = "onkara"
        password = "onkara"
        remote_path = "D:/test_remote_log.txt"
        local_path = "D:/test_copy.log"

        get_remote_log(host, username, password, remote_path, local_path)