import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.123.200', username='tyranno', password='1234', timeout=10)

def run(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    print(stdout.read().decode(), end='')
    e = stderr.read().decode()
    if e: print('ERR:', e, end='')

print("=== mmcblk1p8 파일시스템 타입 ===")
run('sudo blkid /dev/mmcblk1p8 2>&1')
run('sudo file -s /dev/mmcblk1p8 2>&1')

print("\n=== 전체 파티션 ===")
run('sudo blkid 2>&1')

print("\n=== 현재 여유 공간 ===")
run('df -h / && echo "free: $(df -h / | tail -1 | awk \'{print $4}\')"')

print("\n=== /home/pi 삭제 가능 여부 (demo.mp4 등) ===")
run('ls /home/pi/ 2>/dev/null | head -5')

ssh.close()
