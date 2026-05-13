# -*- coding: utf-8 -*-
from __future__ import print_function
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.123.200', username='tyranno', password='1234', timeout=10)

def run(cmd, timeout=60):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    r = (out + err).strip()
    if r: print(r)

print("=== GCP 백업 내 home/tyranno 디렉토리 목록 ===")
run('tar tzf /home/tyranno/gcp-backup-2026-05-13.tar.gz | grep "^home/tyranno/[^/]*/\$" | sort')

print("\n=== 백업 전체 복원 (home/tyranno) ===")
run('tar xzf /home/tyranno/gcp-backup-2026-05-13.tar.gz -C / home/tyranno/lottery home/tyranno/scripts home/tyranno/tools 2>/dev/null || true')

print("\n=== 복원 확인 ===")
run('ls /home/tyranno/lottery/ 2>/dev/null || echo "lottery 없음"')
run('ls /home/tyranno/scripts/ 2>/dev/null || echo "scripts 없음"')
run('ls /home/tyranno/tools/ 2>/dev/null || echo "tools 없음"')

ssh.close()
