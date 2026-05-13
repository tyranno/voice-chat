# -*- coding: utf-8 -*-
from __future__ import print_function
import paramiko, json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.123.200', username='tyranno', password='1234', timeout=10)
sftp = ssh.open_sftp()

def run(cmd, timeout=15):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    r = (out + err).strip()
    if r: print(r)

# 현재 config 읽기
f = sftp.open('/home/tyranno/.openclaw/openclaw.json', 'r')
cfg = json.loads(f.read().decode('utf-8'))
f.close()

# allowedOrigins에 추가
origins = cfg['gateway']['controlUi']['allowedOrigins']
new_origin = 'https://openclaw.tyranno.xyz'
if new_origin not in origins:
    origins.append(new_origin)
    print("추가: " + new_origin)

print("현재 allowedOrigins:", origins)

# 저장
import io
data = json.dumps(cfg, indent=2, ensure_ascii=False).encode('utf-8')
sftp.putfo(io.BytesIO(data), '/home/tyranno/.openclaw/openclaw.json')
sftp.close()

# openclaw 재시작
run('sudo systemctl restart openclaw-gateway')

import time; time.sleep(3)
run('systemctl is-active openclaw-gateway')

ssh.close()
print("완료")
