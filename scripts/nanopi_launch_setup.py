"""
nanopi_setup.sh를 NanoPi에 업로드하고 nohup 백그라운드로 실행
"""
import paramiko, sys

NANOPI_IP = '192.168.123.200'
NANOPI_USER = 'tyranno'
NANOPI_PASS = '1234'

def run(ssh, cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out.strip(): print(out.rstrip())
    if err.strip(): print('ERR:', err.rstrip())
    return out

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(NANOPI_IP, username=NANOPI_USER, password=NANOPI_PASS, timeout=15)

# kill previous apt if still running
run(ssh, 'sudo pkill -f "apt-get update" 2>/dev/null || true')
import time; time.sleep(1)

# upload script
sftp = ssh.open_sftp()
sftp.put(r'e:\Project\My\voice-chat\scripts\nanopi_setup.sh', '/home/tyranno/nanopi_setup.sh')
sftp.close()
run(ssh, 'chmod +x ~/nanopi_setup.sh')

# launch in background
run(ssh, 'nohup bash ~/nanopi_setup.sh > ~/nanopi_setup.log 2>&1 & echo "PID: $!"')
print("백그라운드 설치 시작됨. 진행상황: cat ~/nanopi_setup.log")
ssh.close()
