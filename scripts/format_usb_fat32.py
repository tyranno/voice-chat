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

print("=== 현재 상태 ===")
run('lsblk /dev/mmcblk0')
run('sudo fuser -k /dev/mmcblk0 /dev/mmcblk0p1 2>/dev/null || true')
run('sudo umount /dev/mmcblk0p1 2>/dev/null || true')
time.sleep(2)

print("\n=== 파티션 테이블 새로 작성 + FAT32 포맷 ===")
run_bg('sudo bash -c "parted -s /dev/mmcblk0 mklabel msdos && parted -s /dev/mmcblk0 mkpart primary fat32 0% 100% && sleep 2 && mkfs.fat -F32 -n FLASH /dev/mmcblk0p1" > /tmp/fmt.log 2>&1 &')

print("포맷 중... 30초 대기")
time.sleep(30)
run('cat /tmp/fmt.log')
run('lsblk -o NAME,SIZE,FSTYPE,LABEL /dev/mmcblk0')

ssh.close()
