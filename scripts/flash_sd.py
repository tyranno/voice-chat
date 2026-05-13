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

print("=== 32GB SD 확인 ===")
run('lsblk /dev/mmcblk0')
run('sudo umount /dev/mmcblk0p1 2>/dev/null || true')

print("\n=== 여유 공간 ===")
run('df -h /')

print("\n=== funzip 있나? ===")
run('which funzip 2>/dev/null || echo "없음"')
run('which unzip 2>/dev/null || echo "없음"')

# wget + funzip으로 직접 SD에 스트림
FILE_ID = '1Qk-VfxXfX90OOXIwhsFqnfp66lWTDV3K'
URL = 'https://drive.usercontent.google.com/download?id={}&export=download&confirm=t'.format(FILE_ID)

print("\n=== 다운로드 + SD 쓰기 시작 ===")
print("wget으로 받아서 바로 /dev/mmcblk0 에 씁니다...")
cmd = 'sudo bash -c \'wget -q --show-progress -O - "{}" | funzip | dd of=/dev/mmcblk0 bs=4M conv=fsync 2>/tmp/dd.log\' > /tmp/flash.log 2>&1 & echo $!'.format(URL)
pid = run(cmd)
print("PID: " + pid)

time.sleep(10)
run('cat /tmp/flash.log 2>/dev/null | tail -5')
run('cat /tmp/dd.log 2>/dev/null | tail -3')

ssh.close()
