# -*- coding: utf-8 -*-
from __future__ import print_function
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.123.200', username='tyranno', password='1234', timeout=10)

def run(cmd, timeout=60):
    i,o,e = ssh.exec_command(cmd, timeout=timeout)
    r = (o.read()+e.read()).decode('utf-8','replace').strip()
    if r: print(r)

print("=== GCP 백업에서 opt/voicechat 복원 ===")
run('sudo tar xzf /home/tyranno/gcp-backup-2026-05-13.tar.gz -C / opt/voicechat/oc_proxy.py opt/voicechat/google_stt_server.py opt/voicechat/public 2>/dev/null || true')
run('sudo chown -R tyranno:tyranno /opt/voicechat')
run('ls -la /opt/voicechat/')

print("\n=== oc-proxy 서비스 확인 ===")
run('sudo tar xzf /home/tyranno/gcp-backup-2026-05-13.tar.gz -C / etc/systemd/system/oc-proxy.service 2>/dev/null || true')
run('cat /etc/systemd/system/oc-proxy.service 2>/dev/null || echo "없음"')

print("\n=== openclaw port 확인 (18789 vs 18790) ===")
run('ss -tlnp | grep openclaw')
run('grep LOCAL_OPENCLAW_URL /opt/voicechat/.env')

ssh.close()
