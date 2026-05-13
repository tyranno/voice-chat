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

print("=== udisks2 / automount 중지 ===")
run('sudo systemctl stop udisks2 2>&1 || true')
run('sudo killall mount.exfat 2>&1 || true')
run('sudo killall mkfs.ext4 2>&1 || true')
time.sleep(2)

print("\n=== 커널에서 강제 해제 ===")
run('echo 1 | sudo tee /sys/block/mmcblk0/mmcblk0p1/holders 2>/dev/null || true')
run('sudo blockdev --rereadpt /dev/mmcblk0 2>&1 || true')
time.sleep(2)

print("\n=== 아직 점유 중? ===")
run('sudo fuser /dev/mmcblk0p1 2>&1 || echo "깨끗함"')

print("\n=== wipefs ===")
run('sudo wipefs -af /dev/mmcblk0p1 2>&1')

print("\n=== mkfs.ext4 ===")
run_bg('sudo nohup mkfs.ext4 -F -E nodiscard -L sdcard /dev/mmcblk0p1 > /tmp/mkfs.log 2>&1 &')
time.sleep(8)
run('cat /tmp/mkfs.log')

print("\n20초 대기...")
time.sleep(20)
print("최종 상태:")
run('cat /tmp/mkfs.log | tail -5')
run('pgrep -x mkfs.ext4 && echo "진행중" || echo "완료"')

ssh.close()
