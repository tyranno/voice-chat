import paramiko, sys

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.123.200', username='tyranno', password='1234', timeout=10)

def run(cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out.strip(): print(out.rstrip())
    if err.strip(): print('ERR:', err.rstrip())

print("=== e2fsck 없이 read-only로 마운트 ===")
run('sudo mkdir -p /mnt/userdata')
run('sudo mount -o ro /dev/mmcblk1p8 /mnt/userdata 2>&1 || echo "마운트 실패"')

print("\n=== 마운트 결과 ===")
run('df -h /mnt/userdata 2>/dev/null || echo "마운트 안됨"')

print("\n=== 루트 목록 ===")
run('ls -la /mnt/userdata/ 2>/dev/null || echo "비어있거나 접근 불가"')

print("\n=== 크기 분포 ===")
run('sudo du -sh /mnt/userdata/* /mnt/userdata/.* 2>/dev/null | sort -rh | head -20')

print("\n=== 언마운트 ===")
run('sudo umount /mnt/userdata 2>/dev/null && echo "언마운트 OK"')

ssh.close()
