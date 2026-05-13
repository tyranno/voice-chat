# -*- coding: utf-8 -*-
from __future__ import print_function
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.123.200', username='tyranno', password='1234', timeout=10)

def run(cmd, timeout=15):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if out.strip(): print(out.rstrip())
    if err.strip(): print('ERR: ' + err.rstrip())
    return out.strip()

# 1. config.yml에 SSH 추가
print("=== config.yml 업데이트 ===")
config = """tunnel: 6d00f850-6d23-4469-9fbf-c881e8d4c899
credentials-file: /home/tyranno/.cloudflared/6d00f850-6d23-4469-9fbf-c881e8d4c899.json

ingress:
  - hostname: voicechat.tyranno.xyz
    service: http://localhost:8090
  - hostname: ssh.tyranno.xyz
    service: ssh://localhost:22
  - service: http_status:404
"""

stdin2, stdout2, stderr2 = ssh.exec_command("sudo tee /etc/cloudflared/config.yml > /dev/null")
stdin2.write(config.encode('utf-8'))
stdin2.channel.shutdown_write()
stdout2.read(); stderr2.read()
print("config.yml 업데이트 완료")
run("sudo cat /etc/cloudflared/config.yml")

# 2. DNS 라우팅
print("\n=== DNS 라우팅 ssh.tyranno.xyz ===")
run('cloudflared tunnel route dns voicechat ssh.tyranno.xyz', timeout=30)

# 3. cloudflared 재시작
print("\n=== cloudflared 재시작 ===")
run('sudo systemctl restart cloudflared')
import time; time.sleep(3)
run('sudo systemctl status cloudflared --no-pager | head -6')

ssh.close()
print("\n=== 완료 ===")
