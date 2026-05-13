# -*- coding: utf-8 -*-
from __future__ import print_function
import paramiko, os

gcp = paramiko.SSHClient()
gcp.set_missing_host_key_policy(paramiko.AutoAddPolicy())

# voicechat-key2 시도
for keyfile in ['voicechat-key2', 'voicechat-key']:
    try:
        key_path = os.path.expanduser('~/.ssh/' + keyfile)
        key = paramiko.RSAKey.from_private_key_file(key_path)
        gcp.connect('34.64.158.9', username='tyranno', pkey=key, timeout=10)
        print("접속 성공:", keyfile)
        break
    except Exception as e:
        print(keyfile + " 실패:", e)

def run(cmd, timeout=15):
    i,o,e = gcp.exec_command(cmd, timeout=timeout)
    r = (o.read()+e.read()).decode('utf-8','replace').strip()
    if r: print(r)

print("\n=== GCP 서비스 중지 ===")
run('sudo systemctl stop openclaw-gateway voicechat cloudflared 2>/dev/null || true')
run('sudo systemctl disable openclaw-gateway voicechat cloudflared 2>/dev/null || true')
run('systemctl is-active openclaw-gateway voicechat 2>/dev/null || echo "모두 중지됨"')

gcp.close()
print("완료 - 이제 GCP Console에서 VM STOP 하세요")
