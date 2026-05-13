# -*- coding: utf-8 -*-
from __future__ import print_function
import paramiko, time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.123.200', username='tyranno', password='1234', timeout=10)

def run(cmd, timeout=20):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if out.strip(): print(out.rstrip())
    if err.strip(): print('ERR: ' + err.rstrip())
    return out.strip()

print("=== SD카드 파티션 정보 ===")
run('lsblk -o NAME,SIZE,FSTYPE,LABEL,MOUNTPOINT /dev/mmcblk0')

print("\n=== 커널 I/O 에러 확인 ===")
run('dmesg | grep -i "mmcblk0\|mmc0" | tail -20')

print("\n=== 쓰기 테스트 (100MB) ===")
run('sudo dd if=/dev/zero of=/dev/mmcblk0 bs=1M count=100 oflag=direct 2>&1', timeout=30)

print("\n=== 읽기 테스트 (100MB) ===")
run('sudo dd if=/dev/mmcblk0 of=/dev/null bs=1M count=100 2>&1', timeout=30)

print("\n=== 결과: 에러 없으면 정상 ===")
run('dmesg | grep -i "mmcblk0\|error\|timeout" | tail -5')

ssh.close()
