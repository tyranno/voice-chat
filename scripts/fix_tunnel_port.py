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

# config.yml 확인
print("=== 현재 config ===")
run('sudo cat /etc/cloudflared/config.yml')

# 8090으로 수정
print("\n=== 포트 8090으로 수정 ===")
run("sudo sed -i 's|http://localhost:3000|http://localhost:8090|g' /etc/cloudflared/config.yml")
run('sudo cat /etc/cloudflared/config.yml')

# 재시작
print("\n=== cloudflared 재시작 ===")
run('sudo systemctl restart cloudflared')
import time; time.sleep(3)
run('sudo systemctl status cloudflared --no-pager | head -8')

ssh.close()
