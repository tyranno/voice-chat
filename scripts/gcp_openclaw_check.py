import paramiko, sys

GCP_IP = '34.64.164.13'
GCP_USER = 'tyranno'
GCP_KEY = r'C:\Users\tyranno\.ssh\voicechat-key'

gcp = paramiko.SSHClient()
gcp.set_missing_host_key_policy(paramiko.AutoAddPolicy())
key = paramiko.RSAKey.from_private_key_file(GCP_KEY)
gcp.connect(GCP_IP, username=GCP_USER, pkey=key, timeout=15)

def run(ssh, cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out: print(out, end='')
    if err: print('ERR:', err, end='', file=sys.stderr)
    return out

print("=== openclaw 설치 위치 ===")
run(gcp, 'ls -la /usr/lib/node_modules/openclaw/ 2>/dev/null | head -5 || echo "없음"')
run(gcp, 'ls -la /usr/local/lib/node_modules/openclaw/ 2>/dev/null | head -5 || echo "없음"')
run(gcp, 'npm list -g --depth=0 2>/dev/null | grep openclaw || echo "npm global 없음"')
run(gcp, 'openclaw --version 2>/dev/null || echo "openclaw CLI 없음"')

print("\n=== openclaw 설치 크기 ===")
run(gcp, 'du -sh /usr/lib/node_modules/openclaw 2>/dev/null || du -sh /usr/local/lib/node_modules/openclaw 2>/dev/null || echo "없음"')

print("\n=== .openclaw 상세 크기 ===")
run(gcp, 'du -sh /home/tyranno/.openclaw/* 2>/dev/null | sort -rh | head -20')

print("\n=== .openclaw/workspace 크기 ===")
run(gcp, 'du -sh /home/tyranno/.openclaw/workspace/* 2>/dev/null | sort -rh | head -10')
run(gcp, 'du -sh /home/tyranno/.openclaw/workspace/.git 2>/dev/null')

print("\n=== .openclaw/workspace (node_modules 제외) ===")
run(gcp, 'du -sh --exclude="node_modules" /home/tyranno/.openclaw/workspace/ 2>/dev/null')
run(gcp, 'ls /home/tyranno/.openclaw/workspace/ 2>/dev/null')

print("\n=== ~/scripts 내용 ===")
run(gcp, 'ls -la /home/tyranno/scripts/ 2>/dev/null || echo "없음"')

print("\n=== openclaw.json (설정 확인, 민감 정보 마스킹) ===")
run(gcp, 'cat /home/tyranno/.openclaw/openclaw.json 2>/dev/null | python3 -c "import json,sys; d=json.load(sys.stdin); [d.__setitem__(k, \"***\") for k in d if any(x in k.lower() for x in [\"key\",\"token\",\"secret\",\"pass\"])]; print(json.dumps(d, indent=2, ensure_ascii=False))" 2>/dev/null || echo "없음"')

gcp.close()
