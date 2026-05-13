# -*- coding: utf-8 -*-
from __future__ import print_function
import paramiko, time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.123.200', username='tyranno', password='1234', timeout=10)

def run(cmd, timeout=15):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    r = (out + err).strip()
    if r: print(r)
    return r

print("60초 대기 중...")
time.sleep(60)
print("=== 포맷 로그 ===")
run('cat /tmp/format_sd.log')
print("\n=== 완료 여부 ===")
run('pgrep -f format_sd.sh && echo "진행중" || echo "완료"')

ssh.close()
