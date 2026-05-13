# -*- coding: utf-8 -*-
from __future__ import print_function
import paramiko, time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.123.200', username='tyranno', password='1234', timeout=10)

def run(cmd, timeout=300):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    r = (out + err).strip()
    if r: print(r)
    return r

print("=== apt update ===")
run('sudo apt-get update -y', timeout=120)

print("\n=== 기본 도구 설치 ===")
run('sudo apt-get install -y git ffmpeg python3-pip jq curl wget unzip', timeout=300)

print("\n=== Node.js 22 (NodeSource) ===")
run('curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -', timeout=120)
run('sudo apt-get install -y nodejs', timeout=120)
run('node --version')
run('npm --version')

print("\n=== yt-dlp ===")
run('sudo curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_linux_aarch64 -o /usr/local/bin/yt-dlp', timeout=60)
run('sudo chmod +x /usr/local/bin/yt-dlp')
run('yt-dlp --version')

print("\n=== deno ===")
run('sudo curl -L https://github.com/denoland/deno/releases/latest/download/deno-aarch64-unknown-linux-gnu.zip -o /tmp/deno.zip', timeout=60)
run('sudo unzip -o /tmp/deno.zip -d /usr/local/bin/')
run('sudo chmod +x /usr/local/bin/deno')
run('deno --version')

print("\n=== cloudflared ===")
run('sudo curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64 -o /usr/local/bin/cloudflared', timeout=60)
run('sudo chmod +x /usr/local/bin/cloudflared')
run('cloudflared --version')

print("\n=== Phase 6 완료 ===")
ssh.close()
