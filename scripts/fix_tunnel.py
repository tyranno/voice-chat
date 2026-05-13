# -*- coding: utf-8 -*-
from __future__ import print_function
import paramiko, time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.123.200', username='tyranno', password='1234', timeout=10)

def run(cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    r = (out + err).strip()
    if r: print(r)
    return r

config = """tunnel: 6d00f850-6d23-4469-9fbf-c881e8d4c899
credentials-file: /home/tyranno/.cloudflared/6d00f850-6d23-4469-9fbf-c881e8d4c899.json

ingress:
  - hostname: voicechat.tyranno.xyz
    service: http://localhost:8090
  - hostname: openclaw.tyranno.xyz
    service: http://localhost:18789
  - service: http_status:404
"""

sftp = ssh.open_sftp()
import io
sftp.putfo(io.BytesIO(config.encode('utf-8')), '/home/tyranno/.cloudflared/config.yml')
sftp.close()

print("=== config 수정 확인 ===")
run('cat /home/tyranno/.cloudflared/config.yml')

print("\n=== cloudflared 재시작 ===")
run('sudo systemctl restart cloudflared')
time.sleep(3)

print("\n=== DNS 라우팅 추가 ===")
run('cloudflared tunnel route dns 6d00f850-6d23-4469-9fbf-c881e8d4c899 openclaw.tyranno.xyz', timeout=30)

print("\n=== cloudflared 재시작 ===")
run('sudo systemctl restart cloudflared')
time.sleep(3)

print("\n=== 로컬 health ===")
run('curl -s http://localhost:8090/health')
run('curl -s http://localhost:18789/ 2>/dev/null | head -3 || echo "openclaw 응답 확인 필요"')

ssh.close()
