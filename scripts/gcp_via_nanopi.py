# -*- coding: utf-8 -*-
from __future__ import print_function
import paramiko, os

nano = paramiko.SSHClient()
nano.set_missing_host_key_policy(paramiko.AutoAddPolicy())
nano.connect('192.168.123.200', username='tyranno', password='1234', timeout=10)
sftp = nano.open_sftp()

def run(cmd, timeout=30):
    i,o,e = nano.exec_command(cmd, timeout=timeout)
    r = (o.read()+e.read()).decode('utf-8','replace').strip()
    if r: print(r)

run('mkdir -p /home/tyranno/.ssh')

key_path = os.path.expanduser('~/.ssh/voicechat-key')
sftp.put(key_path, '/home/tyranno/.ssh/voicechat-key')
sftp.close()

run('chmod 700 /home/tyranno/.ssh && chmod 600 /home/tyranno/.ssh/voicechat-key')

print("=== NanoPi -> GCP SSH 시도 ===")
run('ssh -i ~/.ssh/voicechat-key -o StrictHostKeyChecking=no -o ConnectTimeout=10 tyranno@34.64.158.9 "sudo systemctl stop openclaw-gateway voicechat cloudflared 2>/dev/null; echo DONE"', timeout=30)

run('rm ~/.ssh/voicechat-key')
nano.close()
