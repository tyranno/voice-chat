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

print("=== overlay upper layer (userdata2/root) 크기 ===")
run('sudo du -sh /media/pi/userdata2/root/* 2>/dev/null | sort -rh | head -15')

print("\n=== overlay 구조 확인 (mountinfo) ===")
run('cat /proc/mounts | grep overlay')
run('cat /proc/mounts | grep mmcblk')

print("\n=== upper layer 여유 (mmcblk1p8) ===")
run('sudo tune2fs -l /dev/mmcblk1p8 2>/dev/null | grep -E "(block count|Free blocks|Block size)"')

print("\n=== 실제 사용량 계산 ===")
run('sudo df -h /media/pi/userdata2 2>/dev/null || '
    'echo "직접 df 불가 — mmcblk1p8 여유 블록 계산"')

ssh.close()
