import paramiko, sys

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.123.200', username='tyranno', password='1234', timeout=10)

def run(ssh, cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out: print(out, end='')
    if err: print('ERR:', err, end='')
    return out

print("=== 설치 상태 확인 ===")
run(ssh, 'git --version 2>/dev/null || echo "git 없음"')
run(ssh, 'node --version 2>/dev/null || echo "node 없음"')
run(ssh, 'nginx -v 2>&1 || echo "nginx 없음"')
run(ssh, 'ffmpeg -version 2>&1 | head -1 || echo "ffmpeg 없음"')
run(ssh, 'yt-dlp --version 2>/dev/null || echo "yt-dlp 없음"')
run(ssh, 'df -h / | tail -1')
run(ssh, 'ps aux | grep -E "apt|npm|nvm" | grep -v grep || echo "설치 프로세스 없음"')

ssh.close()
