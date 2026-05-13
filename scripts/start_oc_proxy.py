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

print("=== oc_proxy.py 내용 ===")
run('cat /opt/voicechat/oc_proxy.py')

print("\n=== oc-proxy 서비스 시작 ===")
run('sudo systemctl daemon-reload')
run('sudo systemctl enable oc-proxy')
run('sudo systemctl start oc-proxy')

import time; time.sleep(2)
run('systemctl is-active oc-proxy')
run('ss -tlnp | grep 18790')

ssh.close()
