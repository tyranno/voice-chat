# -*- coding: utf-8 -*-
from __future__ import print_function
import paramiko, json, io, os, base64, time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.123.200', username='tyranno', password='1234', timeout=10)
sftp = ssh.open_sftp()

def run(cmd, timeout=15):
    i,o,e = ssh.exec_command(cmd, timeout=timeout)
    r = (o.read()+e.read()).decode('utf-8','replace').strip()
    if r: print(r)

REQ_ID = 'c6907553-f2ce-4d13-b0b1-76be55c1ab54'

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
