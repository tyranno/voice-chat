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

print("=== voicechat 서비스 상태 ===")
run('sudo systemctl status voicechat --no-pager')

print("\n=== 열린 포트 ===")
run('ss -tlnp | grep -v "127.0.0" | head -20')

ssh.close()
