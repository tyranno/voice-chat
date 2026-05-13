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
    if out.strip(): print(out.rstrip())
    if err.strip(): print('ERR: ' + err.rstrip())
    return out.strip()

def run_bg(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    return stdout.read().decode('utf-8', errors='replace').strip()

print("=== umount ===")
run('sudo umount /dev/mmcblk0p1 2>/dev/null || true')

print("=== ext4 포맷 백그라운드 시작 ===")
pid = run_bg('sudo bash -c "mkfs.ext4 -E nodiscard -L sdcard /dev/mmcblk0p1 > /tmp/mkfs.log 2>&1" & echo $!')
print("PID: " + pid)

print("완료될 때까지 대기 중 (최대 5분)...")
for i in range(30):
    time.sleep(10)
    done = run('pgrep mkfs > /dev/null 2>&1 && echo running || echo done', timeout=5)
    log = run('tail -3 /tmp/mkfs.log 2>/dev/null', timeout=5)
    print("[" + str((i+1)*10) + "s] " + done + " | " + log.replace('\n', ' '))
    if done == 'done':
        break

print("\n=== 포맷 결과 ===")
run('cat /tmp/mkfs.log')

print("\n=== 마운트 + 속도 테스트 ===")
run('sudo mkdir -p /mnt/sdcard && sudo mount /dev/mmcblk0p1 /mnt/sdcard')
run('df -h /mnt/sdcard')
run('sudo dd if=/dev/zero of=/mnt/sdcard/test.bin bs=1M count=100 conv=fsync 2>&1', timeout=120)
run('sudo dd if=/mnt/sdcard/test.bin of=/dev/null bs=1M 2>&1', timeout=30)
run('sudo rm /mnt/sdcard/test.bin')
print("\n=== SD카드 OK ===")

ssh.close()
