import paramiko, sys

GCP_IP = '34.64.164.13'
GCP_USER = 'tyranno'
GCP_KEY = r'C:\Users\tyranno\.ssh\voicechat-key'

gcp = paramiko.SSHClient()
gcp.set_missing_host_key_policy(paramiko.AutoAddPolicy())
key = paramiko.RSAKey.from_private_key_file(GCP_KEY)
gcp.connect(GCP_IP, username=GCP_USER, pkey=key, timeout=15)

def run(ssh, cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out: print(out, end='')
    if err: print('ERR:', err, end='', file=sys.stderr)
    return out

print("=== Node.js / npm 버전 ===")
run(gcp, 'node --version 2>/dev/null || echo "node 없음"')
run(gcp, 'which node 2>/dev/null')
run(gcp, 'ls /usr/local/lib/node_modules/ 2>/dev/null | head -20 || echo "global mods 없음"')

print("\n=== nginx 설정 ===")
run(gcp, 'cat /etc/nginx/sites-enabled/*.conf 2>/dev/null || cat /etc/nginx/sites-enabled/default 2>/dev/null || echo "nginx conf 없음"')

print("\n=== crontab ===")
run(gcp, 'crontab -l 2>/dev/null || echo "없음"')

print("\n=== home 크기 summary ===")
run(gcp, 'du -sh /home/tyranno/.openclaw /home/tyranno/.openclaw_migrated /home/tyranno/lottery /home/tyranno/.claude /home/tyranno/.ssh /home/tyranno/.config 2>/dev/null')

print("\n=== lottery/package.json ===")
run(gcp, 'cat /home/tyranno/lottery/package.json 2>/dev/null')

print("\n=== openclaw-gateway systemd ===")
run(gcp, 'cat /home/tyranno/.config/systemd/user/openclaw-gateway.service 2>/dev/null || echo "없음"')

print("\n=== python3 버전 + 패키지 ===")
run(gcp, 'python3 --version')
run(gcp, 'python3 -m pip list 2>/dev/null | grep -E "(google|numpy|websock)" || echo "패키지 없음"')

print("\n=== yt-dlp 위치 ===")
run(gcp, 'which yt-dlp 2>/dev/null && yt-dlp --version 2>/dev/null || echo "yt-dlp 없음"')

print("\n=== ffmpeg 버전 ===")
run(gcp, 'ffmpeg -version 2>&1 | head -1 || echo "ffmpeg 없음"')

gcp.close()
