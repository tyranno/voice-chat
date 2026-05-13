# -*- coding: utf-8 -*-
from __future__ import print_function
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.123.200', username='tyranno', password='1234', timeout=10)

def run(cmd, timeout=120):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    r = (out + err).strip()
    if r: print(r)
    return r

# tar 내부 구조 확인
print("=== gcp-backup 구조 확인 (상위 20줄) ===")
run('tar tzf /home/tyranno/gcp-backup-2026-05-13.tar.gz 2>/dev/null | head -20')

print("\n=== cloudflared-config 구조 ===")
run('tar tzf /home/tyranno/cloudflared-config.tar.gz 2>/dev/null')

print("\n=== nanopi-voicechat-data 구조 ===")
run('tar tzf /home/tyranno/nanopi-voicechat-data.tar.gz 2>/dev/null | head -20')

print("\n=== nanopi-openclaw 구조 ===")
run('tar tzf /home/tyranno/nanopi-openclaw-latest.tar.gz 2>/dev/null | head -20')

ssh.close()
