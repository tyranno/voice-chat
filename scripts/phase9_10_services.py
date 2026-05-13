# -*- coding: utf-8 -*-
from __future__ import print_function
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.123.200', username='tyranno', password='1234', timeout=10)
sftp = ssh.open_sftp()

def run(cmd, timeout=120):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    r = (out + err).strip()
    if r: print(r)
    return r

# === voicechat.service ===
voicechat_service = """[Unit]
Description=VoiceChat Server
After=network.target

[Service]
Type=simple
User=tyranno
WorkingDirectory=/opt/voicechat
EnvironmentFile=/opt/voicechat/.env
ExecStart=/opt/voicechat/voicechat-server
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
"""

# === cloudflared.service ===
cloudflared_service = """[Unit]
Description=Cloudflare Tunnel
After=network.target

[Service]
Type=simple
User=tyranno
ExecStart=/usr/local/bin/cloudflared tunnel --config /home/tyranno/.cloudflared/config.yml run
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""

print("=== voicechat systemd 등록 ===")
sftp.putfo(__import__('io').BytesIO(voicechat_service.encode('utf-8')), '/home/tyranno/voicechat.service')
run('sudo mv /home/tyranno/voicechat.service /etc/systemd/system/voicechat.service')
run('sudo chmod 644 /etc/systemd/system/voicechat.service')

print("\n=== cloudflared systemd 등록 ===")
sftp.putfo(__import__('io').BytesIO(cloudflared_service.encode('utf-8')), '/home/tyranno/cloudflared.service')
run('sudo mv /home/tyranno/cloudflared.service /etc/systemd/system/cloudflared.service')
run('sudo chmod 644 /etc/systemd/system/cloudflared.service')

print("\n=== Phase 10: openclaw 설치 ===")
run('sudo npm install -g openclaw', timeout=180)
run('openclaw --version 2>/dev/null || echo "설치 확인 필요"')

print("\n=== systemd reload + 서비스 시작 ===")
run('sudo systemctl daemon-reload')
run('sudo systemctl enable voicechat cloudflared')
run('sudo systemctl start voicechat')
run('sudo systemctl start cloudflared')

import time
time.sleep(5)

print("\n=== 서비스 상태 확인 ===")
run('systemctl is-active voicechat cloudflared')
run('sudo journalctl -u voicechat -n 10 --no-pager')

sftp.close()
ssh.close()
print("\n=== Phase 9+10 완료 ===")
