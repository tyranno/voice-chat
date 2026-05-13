import paramiko, sys
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.123.200', username='tyranno', password='1234', timeout=10)

def run(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out: print(out, end='')
    if err: print('ERR:', err, end='')

run('df -h /media/pi/userdata2 2>/dev/null || echo "not mounted?"')
run('echo "---"')
run('ls -la /media/pi/userdata2/ 2>/dev/null || echo "empty or not accessible"')
run('echo "---"')
run('sudo du -sh /media/pi/userdata2/* 2>/dev/null | sort -rh | head -15')
ssh.close()
