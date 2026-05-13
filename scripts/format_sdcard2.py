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

def run_bg(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    return out + err

print("=== 점유 프로세스 확인 ===")
run('sudo fuser /dev/mmcblk0p1 2>&1 || echo "없음"')
run('sudo lsof /dev/mmcblk0p1 2>&1 | head -5 || echo "없음"')

print("\n=== 강제 umount + 시그널처리 ===")
run('sudo umount -f /dev/mmcblk0p1 2>&1 || true')
run('sudo blockdev --flushbufs /dev/mmcblk0 2>&1 || true')

print("\n=== wipefs로 시그니처 삭제 ===")
run('sudo wipefs -a /dev/mmcblk0p1 2>&1')

print("\n=== ext4 포맷 시작 (백그라운드) ===")
run_bg('sudo nohup mkfs.ext4 -F -E nodiscard -L sdcard /dev/mmcblk0p1 > /tmp/mkfs.log 2>&1 &')
time.sleep(5)
run('cat /tmp/mkfs.log')

print("\n대기 중 (30초)...")
time.sleep(30)
run('cat /tmp/mkfs.log | tail -5')

done = run('pgrep -x mkfs.ext4 > /dev/null 2>&1 && echo running || echo done', timeout=5)
print("상태: " + done)

if 'done' in done:
    print("\n=== 마운트 테스트 ===")
    run('sudo mkdir -p /mnt/sdcard && sudo mount /dev/mmcblk0p1 /mnt/sdcard && df -h /mnt/sdcard')

ssh.close()
