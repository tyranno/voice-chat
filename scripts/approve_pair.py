# -*- coding: utf-8 -*-
from __future__ import print_function
import paramiko, json, io, os, sys, base64, time

# 환경변수로 비밀정보 분리 (평문 commit 방지)
#   NANOPI_SSH_PASSWORD: NanoPi tyranno user password
#   PAIR_REQ_ID 또는 argv[1]: 승인할 pending 요청 ID (UUID)
PASSWORD = os.environ.get('NANOPI_SSH_PASSWORD')
if not PASSWORD:
    raise SystemExit('NANOPI_SSH_PASSWORD env var required')

REQ_ID = os.environ.get('PAIR_REQ_ID') or (sys.argv[1] if len(sys.argv) > 1 else None)
if not REQ_ID:
    raise SystemExit('PAIR_REQ_ID env var or argv[1] required (pending request UUID)')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.123.200', username='tyranno', password=PASSWORD, timeout=10)
sftp = ssh.open_sftp()

def run(cmd, timeout=15):
    i,o,e = ssh.exec_command(cmd, timeout=timeout)
    r = (o.read()+e.read()).decode('utf-8','replace').strip()
    if r: print(r)

f = sftp.open('/home/tyranno/.openclaw/devices/pending.json', 'r')
pending = json.loads(f.read().decode('utf-8'))
f.close()

f = sftp.open('/home/tyranno/.openclaw/devices/paired.json', 'r')
paired = json.loads(f.read().decode('utf-8'))
f.close()

if REQ_ID not in pending:
    print("pending에 없음 - 목록:", list(pending.keys()))
else:
    entry = pending[REQ_ID]
    device_id = entry['deviceId']
    now_ms = int(time.time() * 1000)
    token = base64.urlsafe_b64encode(os.urandom(32)).rstrip(b'=').decode('ascii')

    paired[device_id] = {
        'deviceId': device_id,
        'publicKey': entry['publicKey'],
        'platform': entry['platform'],
        'clientId': entry['clientId'],
        'clientMode': entry['clientMode'],
        'role': entry['role'],
        'roles': entry['roles'],
        'scopes': entry['scopes'],
        'approvedScopes': entry['scopes'],
        'tokens': {
            'operator': {
                'token': token,
                'role': 'operator',
                'scopes': entry['scopes'],
                'createdAtMs': now_ms
            }
        },
        'createdAtMs': now_ms,
        'approvedAtMs': now_ms
    }
    del pending[REQ_ID]

    sftp.putfo(io.BytesIO(json.dumps(paired, indent=2).encode('utf-8')), '/home/tyranno/.openclaw/devices/paired.json')
    sftp.putfo(io.BytesIO(json.dumps(pending, indent=2).encode('utf-8')), '/home/tyranno/.openclaw/devices/pending.json')
    print("승인 완료:", device_id)

sftp.close()
run('sudo systemctl restart openclaw-gateway')
time.sleep(3)
run('systemctl is-active openclaw-gateway')
ssh.close()
