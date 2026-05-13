# -*- coding: utf-8 -*-
from __future__ import print_function
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.123.110', username='tyranno', password='1234', timeout=10)

def run(cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    r = (out + err).strip()
    if r: print(r)
    return r

CONN = 'U+NetEAEC_5G'

print("=== 고정 IP 192.168.123.200 설정 ===")
run('sudo nmcli con mod "%s" ipv4.addresses 192.168.123.200/24 ipv4.gateway 192.168.123.1 ipv4.dns "8.8.8.8 8.8.4.4" ipv4.method manual' % CONN)
run('sudo nmcli con up "%s"' % CONN)

print("\n=== 적용 후 IP 확인 ===")
run('ip addr show wlan0 | grep inet')
ssh.close()
