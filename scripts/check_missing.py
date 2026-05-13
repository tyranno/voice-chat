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

print("=== /opt/voicechat 전체 ===")
run('ls -la /opt/voicechat/')

print("\n=== firebase-sa.json 존재? ===")
run('ls -la /opt/voicechat/firebase-sa.json 2>/dev/null || echo "없음"')

print("\n=== .env 내용 ===")
run('cat /opt/voicechat/.env')

print("\n=== GCP 백업에서 opt/voicechat 있나? ===")
run('tar tzf /home/tyranno/gcp-backup-2026-05-13.tar.gz | grep "opt/voicechat" | head -10')

ssh.close()
