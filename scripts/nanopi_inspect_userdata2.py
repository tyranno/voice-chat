import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.123.200', username='tyranno', password='1234', timeout=10)

def run(cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out.strip(): print(out.rstrip())
    if err.strip(): print('ERR:', err.rstrip())

print("=== /media/pi/userdata2 크기 ===")
run('df -h /media/pi/userdata2 2>/dev/null || echo "없음"')

print("\n=== 루트 목록 ===")
run('sudo ls -la /media/pi/userdata2/ 2>/dev/null || echo "비어있거나 접근 불가"')

print("\n=== 크기 분포 ===")
run('sudo du -sh /media/pi/userdata2/* /media/pi/userdata2/.* 2>/dev/null | sort -rh | head -20')

ssh.close()
