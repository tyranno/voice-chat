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

run('find /home/tyranno -name "screener.js" -o -name "picker.js" 2>/dev/null')
run('find /home/tyranno/.openclaw -name "stock-screener" -o -name "stock-picker" 2>/dev/null | head -5')

print("\n=== scripts 폴더 ===")
run('ls /home/tyranno/scripts/')

print("\n=== logs 디렉토리 생성 ===")
run('mkdir -p /home/tyranno/scripts/logs')

ssh.close()
