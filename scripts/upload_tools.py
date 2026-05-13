# -*- coding: utf-8 -*-
from __future__ import print_function
import paramiko, os

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.123.200', username='tyranno', password='1234', timeout=10)
sftp = ssh.open_sftp()

def run(cmd, timeout=60):
    i,o,e = ssh.exec_command(cmd, timeout=timeout)
    r = (o.read()+e.read()).decode('utf-8','replace').strip()
    if r: print(r)

def upload_dir(local_dir, remote_dir):
    run('mkdir -p ' + remote_dir)
    for fname in os.listdir(local_dir):
        local_path = os.path.join(local_dir, fname)
        remote_path = remote_dir + '/' + fname
        if os.path.isfile(local_path):
            print('  전송: ' + fname)
            sftp.put(local_path, remote_path)

base_local = r'E:\Project\My\clawdbot-service\tool'
base_remote = '/home/tyranno/tools'

run('mkdir -p ' + base_remote)

for tool in ['stock-screener', 'stock-picker']:
    print('\n=== ' + tool + ' ===')
    upload_dir(os.path.join(base_local, tool), base_remote + '/' + tool)
    run('cd ' + base_remote + '/' + tool + ' && npm install', timeout=120)

print('\n=== 확인 ===')
run('ls ~/tools/stock-screener/ && ls ~/tools/stock-picker/')

sftp.close()
ssh.close()
print('완료')
