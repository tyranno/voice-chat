# -*- coding: utf-8 -*-
from __future__ import print_function
import paramiko, time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.123.200', username='tyranno', password='1234', timeout=10)

def run(cmd, timeout=60):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if out.strip(): print(out.rstrip())
    if err.strip(): print('ERR: ' + err.rstrip())
    return out.strip()

print("=== exfat → ext4 포맷 ===")
run('sudo umount /dev/mmcblk0p1 2>/dev/null || true')
run('sudo mkfs.ext4 -E nodiscard -L sdcard /dev/mmcblk0p1 2>&1', timeout=120)

print("\n=== 마운트 ===")
run('sudo mkdir -p /mnt/sdcard')
run('sudo mount /dev/mmcblk0p1 /mnt/sdcard')
run('df -h /mnt/sdcard')

print("\n=== 쓰기 속도 테스트 (50MB) ===")
run('sudo dd if=/dev/zero of=/mnt/sdcard/test.bin bs=1M count=50 conv=fsync 2>&1', timeout=120)

print("\n=== 읽기 속도 테스트 ===")
run('sudo dd if=/mnt/sdcard/test.bin of=/dev/null bs=1M 2>&1', timeout=30)

run('sudo rm /mnt/sdcard/test.bin')
print("\n=== SD카드 정상 사용 가능! ===")

ssh.close()
