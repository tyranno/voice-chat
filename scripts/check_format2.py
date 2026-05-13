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

print("=== 프로세스 확인 ===")
run('ps aux | grep -E "format|mkfs|wipefs|udisk|parted" | grep -v grep')

print("\n=== /tmp 파일 확인 ===")
run('ls -la /tmp/format* /tmp/nohup* 2>/dev/null || echo "없음"')

print("\n=== nohup.out ===")
run('cat /root/nohup.out 2>/dev/null || cat /home/tyranno/nohup.out 2>/dev/null || echo "없음"')

print("\n=== mmcblk0 현재 상태 ===")
run('lsblk /dev/mmcblk0')
run('sudo fuser /dev/mmcblk0p1 2>&1 || echo "점유 없음"')

ssh.close()
