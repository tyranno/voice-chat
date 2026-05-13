# -*- coding: utf-8 -*-
from __future__ import print_function
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.123.200', username='tyranno', password='1234', timeout=10)

def run(cmd, timeout=15):
    i,o,e = ssh.exec_command(cmd, timeout=timeout)
    r = (o.read()+e.read()).decode('utf-8','replace').strip()
    if r: print(r)

print("=== 서비스 상태 ===")
run('systemctl is-active voicechat cloudflared openclaw-gateway oc-proxy')

print("\n=== 텔레그램 충돌 해결됐나? ===")
run('sudo journalctl -u openclaw-gateway -n 5 --no-pager | grep -E "telegram|conflict|error" | tail -3')

ssh.close()
