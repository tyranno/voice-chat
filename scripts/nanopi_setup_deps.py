"""
NanoPi 환경 설치:
- git, curl, build-essential
- Node.js 22 via nvm
- nginx
- ffmpeg
- yt-dlp
- Python3 + google-cloud-speech deps
"""
import paramiko, sys, time

NANOPI_IP = '192.168.123.200'
NANOPI_USER = 'tyranno'
NANOPI_PASS = '1234'

def run(ssh, cmd, timeout=300):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    stdout.channel.settimeout(timeout)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out.strip(): print(out.rstrip())
    if err.strip(): print('ERR:', err.rstrip(), file=sys.stderr)
    return out

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(NANOPI_IP, username=NANOPI_USER, password=NANOPI_PASS, timeout=15)

print("=== 1. 기본 패키지 ===")
run(ssh, 'sudo apt-get update -qq 2>&1 | tail -3', 120)
run(ssh, 'sudo apt-get install -y git curl build-essential nginx ffmpeg python3-pip python3-venv 2>&1 | tail -5', 300)
run(ssh, 'git --version && nginx -v 2>&1 && ffmpeg -version 2>&1 | head -1')

print("\n=== 2. yt-dlp (최신) ===")
run(ssh, 'sudo curl -sL https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o /usr/local/bin/yt-dlp && sudo chmod +x /usr/local/bin/yt-dlp && yt-dlp --version', 60)

print("\n=== 3. nvm + Node.js 22 ===")
# nvm install
run(ssh, 'curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash 2>&1 | tail -3', 60)
# nvm 환경 로드 후 node 22 설치
run(ssh,
    'export NVM_DIR="$HOME/.nvm" && '
    '[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" && '
    'nvm install 22 2>&1 | tail -5 && '
    'nvm alias default 22 && '
    'node --version && npm --version',
    600)
# 시스템 경로에 심볼릭 링크
run(ssh,
    'export NVM_DIR="$HOME/.nvm" && '
    '[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" && '
    'NODE_BIN=$(which node) && '
    'sudo ln -sf "$NODE_BIN" /usr/local/bin/node && '
    'NPM_BIN=$(which npm) && '
    'sudo ln -sf "$NPM_BIN" /usr/local/bin/npm && '
    'echo "symlinks: node=$(node --version) npm=$(npm --version)"',
    60)

print("\n=== 4. Python3 google-cloud 패키지 ===")
run(ssh, 'pip3 install --user google-cloud-speech numpy websockets 2>&1 | tail -5', 300)

print("\n=== 5. nginx 설정 ===")
nginx_conf = '''server {
    listen 80;
    server_name voicechat.tyranno.xyz localhost;

    location / {
        proxy_pass http://127.0.0.1:8090;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;
    }
}'''
run(ssh, f'echo \'{nginx_conf}\' | sudo tee /etc/nginx/sites-available/voicechat > /dev/null')
run(ssh, 'sudo ln -sf /etc/nginx/sites-available/voicechat /etc/nginx/sites-enabled/voicechat')
run(ssh, 'sudo rm -f /etc/nginx/sites-enabled/default')
run(ssh, 'sudo nginx -t 2>&1 && sudo systemctl enable nginx && sudo systemctl restart nginx && echo "nginx OK"')

print("\n=== 최종 확인 ===")
run(ssh, 'git --version && node --version && npm --version && yt-dlp --version && ffmpeg -version 2>&1 | head -1')
run(ssh, 'sudo systemctl is-active nginx voicechat')

ssh.close()
print("\n=== 설치 완료 ===")
