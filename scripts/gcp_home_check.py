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

print("=== /home/tyranno 전체 구조 ===")
run(gcp, 'find /home/tyranno -maxdepth 4 -not -path "*/node_modules/*" -not -path "*/.git/objects/*" 2>/dev/null | sort')

print("\n=== /home/tyranno 크기 breakdown ===")
run(gcp, 'du -sh /home/tyranno/* /home/tyranno/.* 2>/dev/null | sort -rh')

print("\n=== /root 구조 (있으면) ===")
run(gcp, 'sudo ls -la /root/ 2>/dev/null | head -30')

print("\n=== /home/tyranno/.openclaw 있는지 ===")
run(gcp, 'ls -la /home/tyranno/.openclaw/ 2>/dev/null || echo "없음"')

print("\n=== Node.js / npm 버전 ===")
run(gcp, 'node --version 2>/dev/null || echo "node 없음"')
run(gcp, 'npm --version 2>/dev/null || echo "npm 없음"')
run(gcp, 'which node 2>/dev/null')

print("\n=== nginx 설치 여부 ===")
run(gcp, 'nginx -v 2>&1 || echo "nginx 없음"')
run(gcp, 'ls /etc/nginx/sites-enabled/ 2>/dev/null || echo "nginx sites 없음"')

print("\n=== crontab ===")
run(gcp, 'crontab -l 2>/dev/null || echo "crontab 없음"')

print("\n=== 실행 중인 node 프로세스 ===")
run(gcp, 'ps aux | grep node | grep -v grep || echo "없음"')

print("\n=== /opt 전체 ===")
run(gcp, 'sudo find /opt -maxdepth 4 -not -path "*/node_modules/*" 2>/dev/null | sort')

gcp.close()
