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

TOKEN = '4d0a7071ec1b6a6ca7f7550f93d098fb9542b06d4f3e14bc'

print("=== 로컬에서 토큰 테스트 ===")
run('curl -s http://localhost:18789/ -H "Authorization: Bearer ' + TOKEN + '" | head -2')
run('curl -s -o /dev/null -w "%{http_code}" http://localhost:18789/gateway/status -H "Authorization: Bearer ' + TOKEN + '"')

print("\n=== openclaw-gateway 서비스 커맨드 ===")
run('systemctl cat openclaw-gateway | grep ExecStart')

print("\n=== openclaw 로그 최근 ===")
run('sudo journalctl -u openclaw-gateway -n 5 --no-pager')

ssh.close()
