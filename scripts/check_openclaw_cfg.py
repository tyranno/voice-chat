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
    r = (out + err).strip()
    if r: print(r)

run('find /home/tyranno/.openclaw -name "*.json" | head -10')
run('ls /home/tyranno/.openclaw/')
run('cat /home/tyranno/.openclaw/openclaw.json 2>/dev/null || echo "없음"')

ssh.close()
