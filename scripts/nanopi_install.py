"""
NanoPi 서버 설치:
 - /opt/voicechat 디렉토리 구조 생성
 - .env 파일 생성 (BRIDGE_TLS_ENABLED=false, PORT=8090)
 - voicechat-server-arm64 업로드
 - systemd 서비스 설치 및 활성화
"""
import paramiko, os, sys

NANOPI_IP = '192.168.123.200'
NANOPI_USER = 'tyranno'
NANOPI_PASS = '1234'

ENV_CONTENT = """PORT=8090
BRIDGE_PORT=9090
ACCESS_CODE=z1tG2WUASudHNOj8kMieJCm4EgnpvaK9
BRIDGE_TOKEN=oqcAeiu3fkPF9hmSJjnN1ELGMQgp7B05
TLS_ENABLED=false
DATA_DIR=/opt/voicechat/data
VOSK_URL=ws://127.0.0.1:2700
GOOGLE_TTS_API_KEY=AIzaSyAAR5N629kP8G5IeT-9ZbU-pvyXrZ2FNnE
FCM_SERVICE_ACCOUNT=/opt/voicechat/firebase-sa.json
LOCAL_OPENCLAW_URL=http://localhost:18790
LOCAL_OPENCLAW_NAME=서버 (NanoPi)
LOCAL_OPENCLAW_TOKEN=4d0a7071ec1b6a6ca7f7550f93d098fb9542b06d4f3e14bc
BRIDGE_TLS_ENABLED=false
"""

SERVICE_CONTENT = """[Unit]
Description=Voice Chat Server
After=network.target

[Service]
Type=simple
User=voicechat
Group=voicechat
WorkingDirectory=/opt/voicechat
ExecStart=/opt/voicechat/voicechat-server
Restart=always
RestartSec=5
EnvironmentFile=/opt/voicechat/.env
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/voicechat

[Install]
WantedBy=multi-user.target
"""

def run(ssh, cmd, check=True):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out:
        print(out, end='')
    if err:
        print('ERR:', err, end='', file=sys.stderr)
    return out

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(NANOPI_IP, username=NANOPI_USER, password=NANOPI_PASS, timeout=15)

print("=== 1. 사용자/디렉토리 생성 ===")
run(ssh, 'id voicechat 2>/dev/null || sudo useradd --system --no-create-home --shell /usr/sbin/nologin voicechat')
run(ssh, 'sudo mkdir -p /opt/voicechat/data')
run(ssh, 'sudo chown -R voicechat:voicechat /opt/voicechat')

print("=== 2. .env 파일 생성 ===")
run(ssh, f"echo '{ENV_CONTENT.strip()}' | sudo tee /opt/voicechat/.env > /dev/null")
run(ssh, 'sudo chmod 600 /opt/voicechat/.env')
run(ssh, 'sudo chown voicechat:voicechat /opt/voicechat/.env')
print("   .env 생성 OK")

print("=== 3. systemd 서비스 파일 생성 ===")
run(ssh, f"echo '{SERVICE_CONTENT.strip()}' | sudo tee /etc/systemd/system/voicechat.service > /dev/null")
run(ssh, 'sudo systemctl daemon-reload')
run(ssh, 'sudo systemctl enable voicechat')
print("   서비스 등록 OK")

print("=== 4. binary 업로드 ===")
binary_path = r'e:\Project\My\voice-chat-server\voicechat-server-arm64'
if not os.path.exists(binary_path):
    print("ERROR: binary not found at", binary_path)
    sys.exit(1)

sftp = ssh.open_sftp()
print(f"   uploading {os.path.getsize(binary_path)/1024/1024:.1f} MB ...")
sftp.put(binary_path, '/tmp/voicechat-server')
sftp.close()

run(ssh, 'sudo mv /tmp/voicechat-server /opt/voicechat/voicechat-server')
run(ssh, 'sudo chmod +x /opt/voicechat/voicechat-server')
run(ssh, 'sudo chown voicechat:voicechat /opt/voicechat/voicechat-server')
print("   binary 업로드 OK")

print("=== 5. 서비스 시작 ===")
run(ssh, 'sudo systemctl start voicechat')
import time; time.sleep(2)
run(ssh, 'sudo systemctl status voicechat --no-pager -l | head -20')

print("=== 6. 헬스 체크 ===")
run(ssh, 'curl -s http://localhost:8090/health || echo "HEALTH FAIL"')

ssh.close()
print("\n=== 설치 완료 ===")
