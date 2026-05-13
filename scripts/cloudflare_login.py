# -*- coding: utf-8 -*-
from __future__ import print_function
import paramiko, time, sys

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.123.200', username='tyranno', password='1234', timeout=10)

print("cloudflared tunnel login ...")

transport = ssh.get_transport()
chan = transport.open_session()
chan.set_combine_stderr(True)
chan.exec_command('cloudflared tunnel login')

for _ in range(120):
    time.sleep(1)
    if chan.recv_ready():
        chunk = chan.recv(4096).decode('utf-8', errors='replace')
        sys.stdout.write(chunk)
        sys.stdout.flush()
    if chan.exit_status_ready():
        while chan.recv_ready():
            chunk = chan.recv(4096).decode('utf-8', errors='replace')
            sys.stdout.write(chunk)
        rc = chan.recv_exit_status()
        print("\n[exit: " + str(rc) + "]")
        break

chan.close()
ssh.close()
