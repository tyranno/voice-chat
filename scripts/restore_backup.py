# -*- coding: utf-8 -*-
from __future__ import print_function
import paramiko, os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.123.110', username='tyranno', password='1234', timeout=10)
sftp = ssh.open_sftp()

def run(cmd, timeout=60):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    r = (out + err).strip()
    if r: print(r)
    return r

backup_base = r'E:\Project\My\gcp-backup'

files = [
    ('gcp-backup-2026-05-13.tar.gz', '/home/tyranno/'),
    ('crontab-tyranno.txt', '/home/tyranno/'),
    (r'nanopi-extra\cloudflared-config.tar.gz', '/home/tyranno/'),
    (r'nanopi-extra\nanopi-env.txt', '/home/tyranno/'),
    (r'nanopi-extra\nanopi-voicechat-data.tar.gz', '/home/tyranno/'),
    (r'nanopi-extra\nanopi-openclaw-latest.tar.gz', '/home/tyranno/'),
]

run('mkdir -p /home/tyranno/nanopi-extra')

for src_rel, dst_dir in files:
    src = os.path.join(backup_base, src_rel)
    fname = os.path.basename(src_rel)
    dst = dst_dir + fname
    if os.path.exists(src):
        size = os.path.getsize(src)
        print("전송 중: %s (%dMB)" % (fname, size/1024/1024))
        sftp.put(src, dst)
        print("  완료: %s" % dst)
    else:
        print("  없음: %s" % src)

sftp.close()
print("\n=== 전송 완료 ===")
run('ls -lh /home/tyranno/*.tar.gz /home/tyranno/*.txt 2>/dev/null')
ssh.close()
