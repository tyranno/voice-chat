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

print("=== 도구 확인 ===")
run('which funzip unzip wget 2>/dev/null')

print("\n=== umount ===")
run('sudo umount /dev/sda1 2>/dev/null || true')

FILE_ID = '1Qk-VfxXfX90OOXIwhsFqnfp66lWTDV3K'
URL = 'https://drive.usercontent.google.com/download?id={}&export=download&confirm=t'.format(FILE_ID)

print("\n=== 이미지 다운로드 + /dev/sda 에 쓰기 시작 ===")
print("(약 600MB, 10~20분 소요)")

cmd = 'sudo bash -c \'wget -q -O - "{}" 2>/tmp/wget.log | funzip | dd of=/dev/sda bs=4M conv=fsync > /tmp/dd.log 2>&1\' & echo $!'.format(URL)
pid = run(cmd)
print("PID: " + pid)

time.sleep(15)
print("\n=== 15초 후 진행 상황 ===")
run('ls -lh /tmp/wget.log /tmp/dd.log 2>/dev/null')
run('cat /tmp/wget.log 2>/dev/null | tail -3')
run('cat /tmp/dd.log 2>/dev/null | tail -3')
run('ps aux | grep -E "wget|dd|funzip" | grep -v grep | head -5')

ssh.close()
