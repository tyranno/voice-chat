# -*- coding: utf-8 -*-
from __future__ import print_function
import paramiko, json

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.123.200', username='tyranno', password='1234', timeout=10)
sftp = ssh.open_sftp()

f = sftp.open('/home/tyranno/.openclaw/openclaw.json', 'r')
cfg = json.loads(f.read().decode('utf-8'))
f.close()
sftp.close()

token = cfg.get('gateway', {}).get('auth', {}).get('token', 'NOT FOUND')
mode = cfg.get('gateway', {}).get('auth', {}).get('mode', '')
print("mode:", mode)
print("token:", token)

ssh.close()
