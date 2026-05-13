"""
mmcblk1p8 (8.2GB ext4) 마운트 + /home/tyranno 이전
1. e2fsck로 저널 복구
2. /mnt/userdata에 마운트
3. /home/tyranno를 거기로 복사 + 심볼릭 링크
4. fstab에 영구 마운트 등록
"""
import paramiko, sys, time

NANOPI_IP = '192.168.123.200'
NANOPI_USER = 'tyranno'
NANOPI_PASS = '1234'

def run(ssh, cmd, timeout=120):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out.strip(): print(out.rstrip())
    if err.strip(): print('ERR:', err.rstrip())
    return out

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(NANOPI_IP, username=NANOPI_USER, password=NANOPI_PASS, timeout=15)

print("=== 1. e2fsck (저널 복구) ===")
run(ssh, 'sudo e2fsck -fp /dev/mmcblk1p8 2>&1 || true')

print("\n=== 2. 마운트 포인트 생성 + 마운트 ===")
run(ssh, 'sudo mkdir -p /mnt/userdata && sudo mount /dev/mmcblk1p8 /mnt/userdata && df -h /mnt/userdata')

print("\n=== 3. userdata 내용 ===")
run(ssh, 'ls /mnt/userdata/ && du -sh /mnt/userdata/* 2>/dev/null | sort -rh | head -10')

print("\n=== 4. /home/tyranno를 userdata로 이전 ===")
run(ssh, 'sudo mkdir -p /mnt/userdata/home', 15)
run(ssh, 'sudo cp -a /home/tyranno /mnt/userdata/home/', 120)
run(ssh, 'sudo rm -rf /home/tyranno', 30)
run(ssh, 'sudo ln -sf /mnt/userdata/home/tyranno /home/tyranno')
run(ssh, 'ls -la /home/ && ls /home/tyranno/ | head -5')

print("\n=== 5. fstab 등록 (영구 마운트) ===")
# /dev/mmcblk1p8가 이미 fstab에 없으면 추가
run(ssh,
    'grep -q mmcblk1p8 /etc/fstab || '
    'echo "/dev/mmcblk1p8 /mnt/userdata ext4 defaults,nofail 0 2" | sudo tee -a /etc/fstab && '
    'echo "fstab OK"')
run(ssh, 'grep mmcblk1p8 /etc/fstab')

print("\n=== 6. /home/pi demo 파일 삭제 (169MB 절약) ===")
run(ssh, 'sudo rm -f /home/pi/demo.mp4 && echo "demo.mp4 삭제 OK"', 30)

print("\n=== 7. 최종 디스크 상태 ===")
run(ssh, 'df -h')

ssh.close()
print("\n=== 완료: 이제 8GB 여유 공간 사용 가능 ===")
