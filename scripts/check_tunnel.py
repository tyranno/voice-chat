# -*- coding: utf-8 -*-
from __future__ import print_function
import paramiko

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

print("=== cloudflared config ===")
run('cat /home/tyranno/.cloudflared/config.yml')

print("\n=== 로컬 health ===")
run('curl -s http://localhost:8090/health')

print("\n=== cloudflared 로그 ===")
run('sudo journalctl -u cloudflared -n 15 --no-pager')

ssh.close()
