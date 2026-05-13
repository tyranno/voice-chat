# -*- coding: utf-8 -*-
from __future__ import print_function
import paramiko, time, sys

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.123.200', username='tyranno', password='1234', timeout=10)

def run(cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    if out.strip(): print(out.rstrip())
    if err.strip(): print('ERR: ' + err.rstrip())
    return out.strip()

# 1. 터널 생성
print("=== 1. 터널 생성 ===")
result = run('cloudflared tunnel create voicechat', timeout=30)
print(result)

# tunnel UUID 추출
import re
uuid_match = re.search(r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})', result)
if not uuid_match:
    # 이미 있을 수도 있으니 list로 확인
    list_result = run('cloudflared tunnel list', timeout=15)
    uuid_match = re.search(r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})', list_result)

if uuid_match:
    tunnel_id = uuid_match.group(1)
    print("Tunnel ID: " + tunnel_id)
else:
    print("ERROR: tunnel ID not found")
    ssh.close()
    sys.exit(1)

# 2. config.yml 생성
print("\n=== 2. config.yml 생성 ===")
config = """tunnel: {tid}
credentials-file: /home/tyranno/.cloudflared/{tid}.json

ingress:
  - hostname: voicechat.tyranno.xyz
    service: http://localhost:3000
  - service: http_status:404
""".format(tid=tunnel_id)

run("mkdir -p /home/tyranno/.cloudflared")
# write config via echo
config_cmd = "cat > /home/tyranno/.cloudflared/config.yml << 'CFEOF'\n" + config + "CFEOF"
stdin, stdout, stderr = ssh.exec_command(config_cmd)
stdout.read(); stderr.read()
print("config.yml 작성 완료")
run("cat /home/tyranno/.cloudflared/config.yml")

# 3. DNS 라우팅
print("\n=== 3. DNS 라우팅 ===")
run('cloudflared tunnel route dns voicechat voicechat.tyranno.xyz', timeout=30)

# 4. systemd 서비스 설치
print("\n=== 4. systemd 서비스 설치 ===")
run('sudo cloudflared --config /home/tyranno/.cloudflared/config.yml service install', timeout=30)
run('sudo systemctl enable cloudflared', timeout=15)
run('sudo systemctl start cloudflared', timeout=15)
time.sleep(3)
run('sudo systemctl status cloudflared --no-pager', timeout=15)

print("\n=== 완료! voicechat.tyranno.xyz 터널 활성화 ===")
ssh.close()
