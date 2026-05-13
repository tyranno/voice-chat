# -*- coding: utf-8 -*-
from __future__ import print_function
import paramiko

# pi로 sudoers 설정
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.123.110', username='pi', password='pi', timeout=10)

def run(cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    r = (out + err).strip()
    if r: print(r)
    return r

def sudo(cmd, timeout=30):
    return run('echo pi | sudo -S bash -c \'' + cmd.replace("'", "'\\''") + '\'', timeout=timeout)

# tyranno 비번 설정 + NOPASSWD
sudo('echo "tyranno:1234" | chpasswd')
sudo('echo "tyranno ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/tyranno')
sudo('chmod 440 /etc/sudoers.d/tyranno')
ssh.close()

# tyranno로 재접속 확인
print("\n=== tyranno로 SSH 접속 테스트 ===")
ssh2 = paramiko.SSHClient()
ssh2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh2.connect('192.168.123.110', username='tyranno', password='1234', timeout=10)

def run2(cmd, timeout=30):
    stdin, stdout, stderr = ssh2.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    r = (out + err).strip()
    if r: print(r)
    return r

run2('whoami')
run2('sudo whoami')
run2('uname -a')
ssh2.close()
print("완료")
