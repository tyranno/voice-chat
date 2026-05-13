# -*- coding: utf-8 -*-
from __future__ import print_function
import paramiko, time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.123.200', username='tyranno', password='1234', timeout=10)

def run(cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    r = (out + err).strip()
    if r: print(r)
    return r

print("=== mmcblk1 언마운트 ===")
run('sudo umount /dev/mmcblk1p* 2>/dev/null || true')

print("\n=== 파티션 초기화 + ext4 포맷 ===")
run('sudo parted /dev/mmcblk1 --script mklabel gpt mkpart primary ext4 0% 100%', timeout=30)
run('sudo mkfs.ext4 -L sddata /dev/mmcblk1p1', timeout=120)

print("\n=== /data 마운트 ===")
run('sudo mkdir -p /data')
run('sudo mount /dev/mmcblk1p1 /data')
run('sudo chown tyranno:tyranno /data')

print("\n=== fstab 등록 (자동 마운트) ===")
run('sudo bash -c \'echo "LABEL=sddata /data ext4 defaults,nofail 0 2" >> /etc/fstab\'')

print("\n=== 확인 ===")
run('df -h /data')
run('lsblk -f /dev/mmcblk1')

ssh.close()
print("완료")
