# -*- coding: utf-8 -*-
from __future__ import print_function
import paramiko, time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.123.200', username='tyranno', password='1234', timeout=10)

# SFTP로 스크립트 업로드
sftp = ssh.open_sftp()
script = b"""#!/bin/bash
set -e
# 1. 자동마운트 서비스 중지
systemctl stop udisks2 2>/dev/null || true
sleep 1
# 2. 점유 프로세스 강제 종료
fuser -k /dev/mmcblk0p1 2>/dev/null || true
fuser -k /dev/mmcblk0 2>/dev/null || true
sleep 2
# 3. 확인
echo "점유 확인:"
fuser /dev/mmcblk0p1 2>&1 || echo "깨끗함"
# 4. wipefs
wipefs -af /dev/mmcblk0 2>&1
wipefs -af /dev/mmcblk0p1 2>&1
# 5. 새 파티션 테이블 + 파티션 생성
parted -s /dev/mmcblk0 mklabel gpt
parted -s /dev/mmcblk0 mkpart primary ext4 0% 100%
sleep 2
partprobe /dev/mmcblk0
sleep 2
# 6. ext4 포맷
mkfs.ext4 -E nodiscard -L sdcard /dev/mmcblk0p1
echo "=== 포맷 완료 ==="
# 7. 마운트 + 속도 테스트
mkdir -p /mnt/sdcard
mount /dev/mmcblk0p1 /mnt/sdcard
df -h /mnt/sdcard
echo "=== 쓰기 테스트 ==="
dd if=/dev/zero of=/mnt/sdcard/test.bin bs=1M count=200 conv=fsync 2>&1
echo "=== 읽기 테스트 ==="
dd if=/mnt/sdcard/test.bin of=/dev/null bs=1M 2>&1
rm /mnt/sdcard/test.bin
echo "=== SD카드 정상 ==="
"""
f = sftp.open('/tmp/format_sd.sh', 'wb')
f.write(script)
f.close()
sftp.close()

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

run('chmod +x /tmp/format_sd.sh')
print("스크립트 업로드 완료. 백그라운드로 실행...")
run_bg('sudo nohup /tmp/format_sd.sh > /tmp/format_sd.log 2>&1 &')

time.sleep(5)
print("=== 초기 로그 ===")
run('cat /tmp/format_sd.log')

print("\n30초 대기...")
time.sleep(30)
run('cat /tmp/format_sd.log | tail -10')

print("\n포맷 중?")
run('pgrep -f format_sd && echo "진행중" || echo "완료"')
run('cat /tmp/format_sd.log | tail -5')

ssh.close()
