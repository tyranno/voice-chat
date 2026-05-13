# -*- coding: utf-8 -*-
from __future__ import print_function
import paramiko, os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.123.200', username='tyranno', password='1234', timeout=10)
sftp = ssh.open_sftp()

def run(cmd, timeout=120):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    r = (out + err).strip()
    if r: print(r)
    return r

# === Phase 7: 백업 복원 ===
print("=== /opt/voicechat 디렉토리 생성 ===")
run('sudo mkdir -p /opt/voicechat/data')
run('sudo chown -R tyranno:tyranno /opt/voicechat')

print("\n=== cloudflared 설정 복원 ===")
run('sudo tar xzf /home/tyranno/cloudflared-config.tar.gz -C /')
run('sudo chown -R tyranno:tyranno /home/tyranno/.cloudflared')
run('ls /home/tyranno/.cloudflared/')

print("\n=== voicechat data 복원 ===")
run('sudo tar xzf /home/tyranno/nanopi-voicechat-data.tar.gz -C /')
run('sudo chown -R tyranno:tyranno /opt/voicechat')
run('ls /opt/voicechat/data/ | head -5')

print("\n=== openclaw 복원 ===")
run('tar xzf /home/tyranno/nanopi-openclaw-latest.tar.gz -C /')
run('ls /home/tyranno/.openclaw/ | head -10')

print("\n=== .env 설정 ===")
run('cp /home/tyranno/nanopi-env.txt /opt/voicechat/.env')
run('chmod 600 /opt/voicechat/.env')
run('head -5 /opt/voicechat/.env')

print("\n=== crontab 복원 ===")
run('crontab /home/tyranno/crontab-tyranno.txt')
run('crontab -l')

# === Phase 8: voicechat-server 바이너리 전송 ===
print("\n=== voicechat-server 바이너리 전송 ===")
binary_src = r'E:\Project\My\voice-chat-server\voicechat-server-arm64'
if os.path.exists(binary_src):
    size = os.path.getsize(binary_src)
    print("전송 중: %dMB" % (size/1024/1024))
    sftp.put(binary_src, '/home/tyranno/voicechat-server-arm64')
    run('sudo mv /home/tyranno/voicechat-server-arm64 /opt/voicechat/voicechat-server')
    run('sudo chmod +x /opt/voicechat/voicechat-server')
    run('ls -lh /opt/voicechat/voicechat-server')
else:
    print("바이너리 없음: " + binary_src)

sftp.close()
ssh.close()
print("\n=== Phase 7+8 완료 ===")
