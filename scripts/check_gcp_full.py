# -*- coding: utf-8 -*-
from __future__ import print_function
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.123.200', username='tyranno', password='1234', timeout=10)

def run(cmd, timeout=30):
    i,o,e = ssh.exec_command(cmd, timeout=timeout)
    r = (o.read()+e.read()).decode('utf-8','replace').strip()
    if r: print(r)

print("=== GCP 백업 최상위 디렉토리 목록 ===")
run('tar tzf /home/tyranno/gcp-backup-2026-05-13.tar.gz | grep -E "^[^/]+/$|^home/tyranno/[^/]+/$|^opt/[^/]+/$|^etc/" | sort -u | head -40')

print("\n=== 현재 NanoPi home/tyranno 상태 ===")
run('ls -la /home/tyranno/')

print("\n=== /opt 상태 ===")
run('ls -la /opt/')

ssh.close()
