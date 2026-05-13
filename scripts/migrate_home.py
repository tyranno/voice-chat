"""
GCP → NanoPi 홈 디렉토리 마이그레이션:
- ~/lottery/ (로또 프로젝트)
- ~/scripts/ (모닝브리핑, 관심종목)
- ~/.config/ (notion api key 등)
- ~/.openclaw/ (plugin-runtime-deps 제외 — 재설치로 재생성)
- ~/.openclaw_migrated/
- crontab 복원
- openclaw-gateway systemd user 서비스
"""
import paramiko, sys, os, io, time

GCP_IP = '34.64.164.13'
GCP_USER = 'tyranno'
GCP_KEY = r'C:\Users\tyranno\.ssh\voicechat-key'

NANOPI_IP = '192.168.123.200'
NANOPI_USER = 'tyranno'
NANOPI_PASS = '1234'

LOCAL_BACKUP = r'e:\Project\My\voice-chat\scripts\home-backup.tar.gz'

def run(ssh, cmd, timeout=60):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out.strip(): print(out.rstrip())
    if err.strip() and 'warning' not in err.lower(): print('ERR:', err.rstrip(), file=sys.stderr)
    return out

print("=== 1. GCP에서 홈 데이터 압축 (plugin-runtime-deps 제외) ===")
gcp = paramiko.SSHClient()
gcp.set_missing_host_key_policy(paramiko.AutoAddPolicy())
key = paramiko.RSAKey.from_private_key_file(GCP_KEY)
gcp.connect(GCP_IP, username=GCP_USER, pkey=key, timeout=15)

run(gcp,
    'tar czf /tmp/home-backup.tar.gz '
    '--exclude=".openclaw/plugin-runtime-deps" '
    '--exclude=".npm/_cacache" '
    '--exclude=".cache" '
    '--exclude="go/pkg/mod" '
    '--exclude=".vscode-server" '
    '--exclude="lottery/node_modules" '
    '--exclude=".config/gcloud" '
    '-C /home/tyranno '
    'lottery scripts .config .openclaw .openclaw_migrated .bashrc .profile '
    '2>/dev/null; ls -lh /tmp/home-backup.tar.gz',
    300)

print("\n=== 2. GCP에서 openclaw 설치 정보 저장 ===")
run(gcp, 'npm list -g --depth=0 2>/dev/null | grep openclaw')
run(gcp, 'cat /home/tyranno/.config/systemd/user/openclaw-gateway.service 2>/dev/null | tee /tmp/openclaw-gateway.service > /dev/null && echo "service file saved"')
run(gcp, 'crontab -l 2>/dev/null | tee /tmp/crontab-backup.txt > /dev/null && echo "crontab saved"')

print("\n=== 3. 로컬로 다운로드 ===")
sftp_gcp = gcp.open_sftp()
sftp_gcp.get('/tmp/home-backup.tar.gz', LOCAL_BACKUP)
print(f"   home-backup.tar.gz: {os.path.getsize(LOCAL_BACKUP)/1024/1024:.1f} MB 다운로드 완료")

# service file and crontab
sftp_gcp.get('/tmp/openclaw-gateway.service', r'e:\Project\My\voice-chat\scripts\openclaw-gateway.service')
sftp_gcp.get('/tmp/crontab-backup.txt', r'e:\Project\My\voice-chat\scripts\crontab-backup.txt')
sftp_gcp.close()
gcp.close()
print("   서비스 파일 + crontab 다운로드 완료")

print("\n=== 4. NanoPi로 업로드 ===")
nanopi = paramiko.SSHClient()
nanopi.set_missing_host_key_policy(paramiko.AutoAddPolicy())
nanopi.connect(NANOPI_IP, username=NANOPI_USER, password=NANOPI_PASS, timeout=15)

sftp_np = nanopi.open_sftp()
sftp_np.put(LOCAL_BACKUP, '/tmp/home-backup.tar.gz')
sftp_np.put(r'e:\Project\My\voice-chat\scripts\openclaw-gateway.service', '/tmp/openclaw-gateway.service')
sftp_np.put(r'e:\Project\My\voice-chat\scripts\crontab-backup.txt', '/tmp/crontab-backup.txt')
sftp_np.close()
print("   업로드 완료")

print("\n=== 5. NanoPi에 압축 해제 ===")
run(nanopi, 'tar xzf /tmp/home-backup.tar.gz -C /home/tyranno/ 2>&1 || true')
run(nanopi, 'ls /home/tyranno/')

print("\n=== 6. crontab 복원 ===")
run(nanopi, 'crontab /tmp/crontab-backup.txt && echo "crontab 복원 OK" && crontab -l')

print("\n=== 7. openclaw-gateway systemd user 서비스 설치 ===")
run(nanopi, 'mkdir -p /home/tyranno/.config/systemd/user/')
run(nanopi, 'cp /tmp/openclaw-gateway.service /home/tyranno/.config/systemd/user/openclaw-gateway.service')
run(nanopi, 'systemctl --user daemon-reload 2>/dev/null || echo "user systemd not running yet"')
print("   서비스 파일 설치 OK (openclaw 설치 후 활성화 필요)")

print("\n=== 8. lottery node_modules 설치 ===")
run(nanopi,
    'export NVM_DIR="$HOME/.nvm" && [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" && '
    'cd /home/tyranno/lottery && npm install 2>&1 | tail -3',
    120)

print("\n=== 완료 ===")
run(nanopi, 'ls /home/tyranno/lottery/')
run(nanopi, 'crontab -l')
nanopi.close()
