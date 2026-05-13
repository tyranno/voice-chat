# -*- coding: utf-8 -*-
from __future__ import print_function
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.123.200', username='tyranno', password='1234', timeout=10)

def run(cmd, timeout=120):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    r = (out + err).strip()
    if r: print(r)

print("=== lottery npm install ===")
run('cd /home/tyranno/lottery && npm install', timeout=120)

print("\n=== morning_briefing, watchlist_scan 의존성 확인 ===")
run('head -5 /home/tyranno/scripts/morning_briefing.mjs')

ssh.close()
