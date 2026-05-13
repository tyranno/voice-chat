"""
NanoPi 긴급 디스크 정리:
- 데스크탑 GUI 패키지 제거 (lightdm, qt5, opencv 등 - 서버로 쓸거라 불필요)
- /opt 데모 앱 제거
- /home/pi 확인 후 정리
- apt 캐시 정리
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

print("=== 현재 디스크 ===")
run(ssh, 'df -h /')

print("\n=== 상위 디렉토리 크기 ===")
run(ssh, 'sudo du -sh /home/* /opt/* /var/lib/* 2>/dev/null | sort -rh | head -15')

# 1. apt 프로세스 종료
print("\n=== apt 종료 ===")
run(ssh, 'sudo pkill -f apt-get 2>/dev/null || true; sleep 2')

# 2. apt lock 해제
run(ssh, 'sudo rm -f /var/lib/dpkg/lock-frontend /var/lib/dpkg/lock /var/cache/apt/archives/lock 2>/dev/null || true')
run(ssh, 'sudo dpkg --configure -a 2>&1 | head -5 || true')

# 3. /opt 데모 앱 제거 (서버로 쓸거라 불필요)
print("\n=== /opt 데모 앱 제거 ===")
run(ssh, 'sudo rm -rf /opt/dual-camera /opt/opencv-videoprocessor /opt/qt5-qml-image-viewer /opt/qt5-smarthome /opt/teamviewer 2>/dev/null && echo "opt 정리 OK"')
run(ssh, 'ls /opt/')

# 4. /home/pi 내용 확인 (중요 데이터인지)
print("\n=== /home/pi 내용 ===")
run(ssh, 'ls -la /home/pi/ 2>/dev/null | head -20 || echo "없음"')
run(ssh, 'du -sh /home/pi/* 2>/dev/null | sort -rh | head -10')

# 5. apt 캐시 완전 정리
print("\n=== apt 캐시 정리 ===")
run(ssh, 'sudo apt-get clean -y 2>&1')
run(ssh, 'sudo rm -rf /var/lib/apt/lists/* 2>/dev/null && echo "apt lists 삭제 OK"')

# 6. 로그 추가 정리
run(ssh, 'sudo find /var/log -name "*.gz" -delete 2>/dev/null; sudo find /var/log -name "*.old" -delete 2>/dev/null; echo "로그 정리 OK"')

# 7. root 홈의 큰 파일
run(ssh, 'sudo ls -lh /root/ 2>/dev/null | head -10')
run(ssh, 'sudo rm -f /linux-headers-4.4.179.deb 2>/dev/null && echo "linux-headers .deb 삭제"')

print("\n=== 정리 후 디스크 ===")
run(ssh, 'df -h /')
run(ssh, 'sudo du -sh /* 2>/dev/null | sort -rh | head -10')

ssh.close()
