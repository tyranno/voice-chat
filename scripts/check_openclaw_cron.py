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

print("=== openclaw cron jobs ===")
run('cat /home/tyranno/.openclaw/cron/jobs.json')

print("\n=== 시스템 crontab ===")
run('crontab -l')

print("\n=== lottery/scripts 파일 존재 확인 ===")
run('ls /home/tyranno/lottery/ 2>/dev/null || echo "lottery 없음"')
run('ls /home/tyranno/scripts/ 2>/dev/null || echo "scripts 없음"')

ssh.close()
