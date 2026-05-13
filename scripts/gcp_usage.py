import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
key = paramiko.RSAKey.from_private_key_file(r'C:\Users\tyranno\.ssh\voicechat-key')
ssh.connect('34.64.164.13', username='tyranno', pkey=key, timeout=15)

def run(cmd, timeout=15):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode()
    if out.strip(): print(out.rstrip())

print("=== GCP 인스턴스 정보 ===")
run('curl -s -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/machine-type 2>/dev/null | sed "s|.*/||" && echo ""')
run('curl -s -H "Metadata-Flavor: Google" http://metadata.google.internal/computeMetadata/v1/instance/zone 2>/dev/null | sed "s|.*/||" && echo ""')

print("\n=== 디스크 ===")
run('df -h && lsblk')

print("\n=== 메모리 / CPU ===")
run('free -h && nproc && cat /proc/cpuinfo | grep "model name" | head -1')

print("\n=== 전체 home 크기 ===")
run('du -sh /home/tyranno/ 2>/dev/null')
run('du -sh /home/tyranno/.openclaw/ 2>/dev/null')

ssh.close()
