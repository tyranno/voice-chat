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

print("=== umount /dev/sda ===")
run('sudo umount /dev/sda1 2>/dev/null || true')

print("\n=== zip -> /dev/sda 쓰기 시작 ===")
run_bg('sudo bash -c "unzip -p /home/tyranno/rk3399-usb-ubuntu-noble-core-4.19-arm64-20260421.zip | dd of=/dev/sda bs=4M conv=fsync > /tmp/flash.log 2>&1" &')

time.sleep(10)
print("10초 후 상태:")
run('ps aux | grep -E "unzip|dd" | grep -v grep')
run('cat /tmp/flash.log 2>/dev/null | tail -3')

print("\n계속 진행 중... 완료 확인은 check_flash.py 로")
ssh.close()
