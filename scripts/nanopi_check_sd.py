import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.123.200', username='tyranno', password='1234', timeout=10)

def run(cmd, timeout=15):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode()
    if out.strip(): print(out.rstrip())
    e = stderr.read().decode()
    if e.strip(): print('ERR:', e.rstrip())

print("=== 전체 블록 장치 ===")
run('lsblk -o NAME,SIZE,TYPE,MOUNTPOINT,FSTYPE,LABEL')

print("\n=== 디스크 장치 목록 ===")
run('ls -la /dev/mmcblk* /dev/sd* /dev/nvme* 2>/dev/null')

print("\n=== 32GB SD 인식 여부 ===")
run('sudo fdisk -l 2>/dev/null | grep -E "^Disk /dev" | head -10')

ssh.close()
