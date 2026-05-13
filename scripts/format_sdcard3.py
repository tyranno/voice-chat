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
    stdout.read(); stderr.read()

print("=== mount.exfat / mkfs 프로세스 강제 종료 ===")
run('sudo kill -9 1885 2485 3604 2>/dev/null || true')
time.sleep(2)
run('sudo fuser -k /dev/mmcblk0p1 2>/dev/null || true')
time.sleep(2)

print("\n=== wipefs ===")
run('sudo wipefs -a /dev/mmcblk0p1 2>&1')
run('sudo wipefs -a /dev/mmcblk0 2>&1')

print("\n=== ext4 포맷 (백그라운드) ===")
run_bg('sudo nohup mkfs.ext4 -F -E nodiscard -L sdcard /dev/mmcblk0p1 > /tmp/mkfs.log 2>&1 &')
time.sleep(5)
run('cat /tmp/mkfs.log')

print("\n15초 대기...")
time.sleep(15)
run('cat /tmp/mkfs.log | tail -3')

print("\n=== 포맷 완료 확인 ===")
still_running = run('pgrep -x mkfs.ext4 2>/dev/null && echo yes || echo no')
if 'no' in still_running:
    print("포맷 완료!")
    run('sudo mkdir -p /mnt/sdcard && sudo mount /dev/mmcblk0p1 /mnt/sdcard && df -h /mnt/sdcard')
else:
    print("아직 진행 중... /tmp/mkfs.log 확인")
    run('cat /tmp/mkfs.log')

ssh.close()
