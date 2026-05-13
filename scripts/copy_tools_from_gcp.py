# -*- coding: utf-8 -*-
from __future__ import print_function
import paramiko, os

# GCP에서 tools 디렉토리 확인
gcp = paramiko.SSHClient()
gcp.set_missing_host_key_policy(paramiko.AutoAddPolicy())
key = paramiko.RSAKey.from_private_key_file(os.path.expanduser('~/.ssh/voicechat-key'))
gcp.connect('34.64.158.9', username='tyranno', pkey=key, timeout=10)

def grun(cmd, timeout=15):
    i,o,e = gcp.exec_command(cmd, timeout=timeout)
    r = (o.read()+e.read()).decode('utf-8','replace').strip()
    if r: print(r)
    return r

print("=== GCP ~/tools 확인 ===")
grun('ls ~/tools/')
grun('ls ~/tools/stock-screener/ 2>/dev/null | head -5')
grun('ls ~/tools/stock-picker/ 2>/dev/null | head -5')

gcp.close()
