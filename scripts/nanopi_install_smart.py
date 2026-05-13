"""
NanoPi 스마트 설치 (디스크 절약):
- apt lists를 /dev/shm (RAM tmpfs)에 저장해서 디스크 아낌
- nvm으로 Node.js 22 설치 (apt 불필요)
- yt-dlp 바이너리 직접 다운로드 (apt 불필요)
- nginx만 apt로 설치 (tmpfs 활용)
- Python3 패키지는 pip (apt 불필요)
"""
import paramiko, sys, time

NANOPI_IP = '192.168.123.200'
NANOPI_USER = 'tyranno'
NANOPI_PASS = '1234'

def run(ssh, cmd, timeout=60):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out.strip(): print(out.rstrip())
    if err.strip(): print('ERR:', err.rstrip())
    return out

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(NANOPI_IP, username=NANOPI_USER, password=NANOPI_PASS, timeout=15)

print("=== /media 확인 ===")
run(ssh, 'df -h && ls /media/ 2>/dev/null')

print("\n=== 1. yt-dlp 바이너리 직접 설치 ===")
run(ssh, 'sudo curl -sL https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_linux_aarch64 -o /usr/local/bin/yt-dlp && sudo chmod +x /usr/local/bin/yt-dlp && yt-dlp --version', 60)

print("\n=== 2. nvm 설치 ===")
out = run(ssh,
    'export NVM_DIR="$HOME/.nvm" && '
    '[ -s "$NVM_DIR/nvm.sh" ] && echo "nvm already installed" || '
    'curl -sfo- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash 2>&1 | tail -5',
    60)

print("\n=== 3. Node.js 22 설치 (nvm) ===")
# nvm은 백그라운드로 실행 (오래 걸림)
run(ssh,
    'export NVM_DIR="$HOME/.nvm" && [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" && '
    'nohup bash -c "nvm install 22 && nvm alias default 22 && '
    'sudo ln -sf $(which node) /usr/local/bin/node && '
    'sudo ln -sf $(which npm) /usr/local/bin/npm && '
    'echo NODE_INSTALL_DONE" > /tmp/node_install.log 2>&1 &'
    'echo "Node 설치 백그라운드 시작 (PID: $!)"',
    30)

print("\n=== 4. nginx: apt를 tmpfs(RAM)에서 실행 ===")
# /dev/shm에 apt lists 저장 (RAM 사용, 디스크 아낌)
run(ssh, 'sudo mkdir -p /dev/shm/apt-lists/partial', 15)
run(ssh,
    'sudo apt-get update '
    '-o Dir::State::Lists=/dev/shm/apt-lists '
    '-o Dir::Cache::Archives=/dev/shm/apt-archives '
    '2>&1 | tail -5',
    180)
run(ssh,
    'sudo apt-get install -y nginx '
    '-o Dir::State::Lists=/dev/shm/apt-lists '
    '-o Dir::Cache::Archives=/dev/shm/apt-archives '
    '2>&1 | tail -5',
    120)
run(ssh, 'nginx -v 2>&1 && sudo systemctl enable nginx && echo "nginx OK"', 15)

# nginx 설정
print("\n=== 5. nginx 설정 ===")
nginx_conf = (
    'server {\n'
    '    listen 80;\n'
    '    server_name voicechat.tyranno.xyz localhost;\n\n'
    '    location / {\n'
    '        proxy_pass http://127.0.0.1:8090;\n'
    '        proxy_http_version 1.1;\n'
    '        proxy_set_header Upgrade $http_upgrade;\n'
    '        proxy_set_header Connection "upgrade";\n'
    '        proxy_set_header Host $host;\n'
    '        proxy_set_header X-Real-IP $remote_addr;\n'
    '        proxy_read_timeout 600s;\n'
    '        proxy_send_timeout 600s;\n'
    '    }\n'
    '}\n'
)
run(ssh, f'echo "{nginx_conf}" | sudo tee /etc/nginx/sites-available/voicechat > /dev/null')
run(ssh, 'sudo ln -sf /etc/nginx/sites-available/voicechat /etc/nginx/sites-enabled/voicechat')
run(ssh, 'sudo rm -f /etc/nginx/sites-enabled/default')
run(ssh, 'sudo nginx -t 2>&1 && sudo systemctl restart nginx && echo "nginx configured OK"', 30)

print("\n=== 6. Python3 google-cloud 패키지 ===")
run(ssh, 'pip3 install --user google-cloud-speech numpy websockets 2>&1 | tail -5', 300)

print("\n=== 7. /dev/shm apt 정리 ===")
run(ssh, 'sudo rm -rf /dev/shm/apt-lists /dev/shm/apt-archives 2>/dev/null && echo "tmpfs apt 정리 OK"')

print("\n=== 현재 상태 ===")
run(ssh, 'git --version && yt-dlp --version && nginx -v 2>&1')
run(ssh, 'node --version 2>/dev/null || echo "node 설치 중 (백그라운드)..."')
run(ssh, 'df -h /')
run(ssh, 'cat /tmp/node_install.log 2>/dev/null | tail -5')

ssh.close()
print("\n=== 완료 (Node.js는 백그라운드 설치 중) ===")
