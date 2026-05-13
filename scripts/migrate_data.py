"""
GCP /opt/voicechat/data 백업 → 로컬 → NanoPi 복원
firebase-sa.json 도 복사
"""
import paramiko, os, io, sys, tarfile, time

GCP_IP = '34.64.164.13'
GCP_USER = 'tyranno'
GCP_KEY = r'C:\Users\tyranno\.ssh\voicechat-key'

NANOPI_IP = '192.168.123.200'
NANOPI_USER = 'tyranno'
NANOPI_PASS = '1234'

LOCAL_BACKUP = r'e:\Project\My\voice-chat\scripts\vc-data-backup.tar.gz'

print("=== Step 1: GCP에서 백업 파일 생성 ===")
gcp = paramiko.SSHClient()
gcp.set_missing_host_key_policy(paramiko.AutoAddPolicy())
key = paramiko.RSAKey.from_private_key_file(GCP_KEY)
gcp.connect(GCP_IP, username=GCP_USER, pkey=key, timeout=15)

stdin, stdout, stderr = gcp.exec_command(
    'sudo tar czf /tmp/vc-data.tar.gz /opt/voicechat/data /opt/voicechat/firebase-sa.json 2>/dev/null; '
    'sudo chown tyranno /tmp/vc-data.tar.gz; '
    'ls -lh /tmp/vc-data.tar.gz'
)
out = stdout.read().decode()
print(out)

print("=== Step 2: 로컬로 다운로드 ===")
sftp_gcp = gcp.open_sftp()
sftp_gcp.get('/tmp/vc-data.tar.gz', LOCAL_BACKUP)
sftp_gcp.close()
print(f"   다운로드 완료: {os.path.getsize(LOCAL_BACKUP)/1024:.0f} KB")
gcp.close()

print("=== Step 3: NanoPi로 업로드 ===")
nanopi = paramiko.SSHClient()
nanopi.set_missing_host_key_policy(paramiko.AutoAddPolicy())
nanopi.connect(NANOPI_IP, username=NANOPI_USER, password=NANOPI_PASS, timeout=15)

sftp_np = nanopi.open_sftp()
sftp_np.put(LOCAL_BACKUP, '/tmp/vc-data.tar.gz')
sftp_np.close()
print("   업로드 완료")

print("=== Step 4: NanoPi에 압축 해제 ===")
def run(ssh, cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out: print(out, end='')
    if err: print('ERR:', err, end='', file=sys.stderr)
    return out

run(nanopi, 'sudo tar xzf /tmp/vc-data.tar.gz -C / 2>&1 || true')
run(nanopi, 'sudo chown -R voicechat:voicechat /opt/voicechat/data')
run(nanopi, 'sudo chown voicechat:voicechat /opt/voicechat/firebase-sa.json 2>/dev/null || true')
run(nanopi, 'sudo chmod 600 /opt/voicechat/.env')
run(nanopi, 'ls -la /opt/voicechat/')
run(nanopi, 'du -sh /opt/voicechat/data/')

print("\n=== Step 5: 서비스 재시작 ===")
run(nanopi, 'sudo systemctl restart voicechat')
time.sleep(2)
run(nanopi, 'curl -s http://localhost:8090/health')

nanopi.close()
print("\n=== 데이터 마이그레이션 완료 ===")
