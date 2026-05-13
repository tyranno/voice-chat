# -*- coding: utf-8 -*-
from __future__ import print_function
import paramiko, time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.123.200', username='tyranno', password='1234', timeout=10)

def run(cmd, timeout=10):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    r = (out + err).strip()
    if r: print(r)
    return r

run('ps aux | grep -E "unzip|dd " | grep -v grep | head -5')
run('cat /tmp/flash.log 2>/dev/null')
run('sudo kill -USR1 $(pgrep -x dd) 2>/dev/null || true')
time.sleep(1)
run('cat /tmp/flash.log 2>/dev/null | tail -5')

ssh.close()
