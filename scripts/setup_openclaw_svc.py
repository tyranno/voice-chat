# -*- coding: utf-8 -*-
from __future__ import print_function
import paramiko, time

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

print("=== GCP 백업에서 서비스 파일 추출 ===")
run('tar xzf /home/tyranno/gcp-backup-2026-05-13.tar.gz -C /tmp etc/systemd/system/openclaw-gateway.service etc/systemd/system/oc-proxy.service 2>/dev/null || true')
run('cat /tmp/etc/systemd/system/openclaw-gateway.service 2>/dev/null || echo "파일 없음"')

print("\n=== Claude Code CLI 설치 ===")
run('sudo npm install -g @anthropic-ai/claude-code', timeout=180)
run('claude --version 2>/dev/null || echo "설치 확인 필요"')

print("\n=== openclaw-gateway 서비스 설치 ===")
run('sudo cp /tmp/etc/systemd/system/openclaw-gateway.service /etc/systemd/system/ 2>/dev/null || echo "서비스 파일 복사 실패"')
run('cat /etc/systemd/system/openclaw-gateway.service 2>/dev/null')

print("\n=== systemd 등록 ===")
run('sudo systemctl daemon-reload')
run('sudo systemctl enable openclaw-gateway 2>/dev/null || echo "등록 실패"')
run('sudo systemctl start openclaw-gateway 2>/dev/null || echo "시작 실패"')
time.sleep(3)
run('systemctl is-active openclaw-gateway 2>/dev/null')
run('sudo journalctl -u openclaw-gateway -n 10 --no-pager 2>/dev/null')

ssh.close()
