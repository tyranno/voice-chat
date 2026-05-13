"""
NanoPi에 OpenClaw 설치:
- npm install -g openclaw (전역)
- openclaw-gateway systemd user 서비스 활성화
- loginctl enable-linger (로그인 없이 서비스 시작)
"""
import paramiko, sys, time

NANOPI_IP = '192.168.123.200'
NANOPI_USER = 'tyranno'
NANOPI_PASS = '1234'

def run(ssh, cmd, timeout=300):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out.strip(): print(out.rstrip())
    if err.strip(): print('ERR:', err.rstrip(), file=sys.stderr)
    return out

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(NANOPI_IP, username=NANOPI_USER, password=NANOPI_PASS, timeout=15)

print("=== 1. openclaw npm global 설치 ===")
print("    (시간이 걸릴 수 있습니다...)")
out = run(ssh,
    'export NVM_DIR="$HOME/.nvm" && [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" && '
    'npm install -g openclaw 2>&1 | tail -10',
    600)

print("\n=== 2. openclaw 버전 확인 ===")
run(ssh,
    'export NVM_DIR="$HOME/.nvm" && [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" && '
    'openclaw --version 2>/dev/null || '
    '/usr/local/lib/node_modules/openclaw/node_modules/.bin/openclaw --version 2>/dev/null || '
    'echo "openclaw CLI 경로 확인 필요"')

print("\n=== 3. loginctl linger 활성화 (부팅 시 자동 시작) ===")
run(ssh, 'sudo loginctl enable-linger tyranno && echo "linger OK"')

print("\n=== 4. systemd user 서비스 활성화 ===")
# systemd user session 시작
run(ssh, 'XDG_RUNTIME_DIR=/run/user/$(id -u) systemctl --user daemon-reload 2>&1 || true')
run(ssh,
    'XDG_RUNTIME_DIR=/run/user/$(id -u) systemctl --user enable openclaw-gateway 2>&1 && '
    'XDG_RUNTIME_DIR=/run/user/$(id -u) systemctl --user start openclaw-gateway 2>&1 || '
    'echo "서비스 시작 실패 — 수동 시작 필요: systemctl --user start openclaw-gateway"')

time.sleep(3)
print("\n=== 5. 서비스 상태 ===")
run(ssh,
    'XDG_RUNTIME_DIR=/run/user/$(id -u) systemctl --user status openclaw-gateway --no-pager -l 2>&1 | head -20')

print("\n=== 6. 디스크 확인 ===")
run(ssh, 'df -h /')

ssh.close()
print("\n=== openclaw 설치 완료 ===")
