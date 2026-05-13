import paramiko, time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.123.200', username='tyranno', password='1234', timeout=10)

def run(cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out.strip(): print(out.rstrip())
    if err.strip(): print('ERR:', err.rstrip())
    return out.strip()

def run_bg(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    return stdout.read().decode().strip()

# 1. 사전 확인
print("=== 복제 전 확인 ===")
run('lsblk /dev/mmcblk1 /dev/sda')
run('sudo umount /dev/sda1 2>/dev/null || true')

# 2. dd 백그라운드 실행
print("\n=== eMMC → SD 복제 시작 (백그라운드) ===")
print("14.6GB 복제 중... 약 10~20분 소요")
pid = run_bg('sudo nohup dd if=/dev/mmcblk1 of=/dev/sda bs=4M conv=fsync 2>/home/tyranno/dd_progress.log & echo $!')
print(f"dd PID: {pid}")

# 3. 진행 상황 모니터링 (SIGUSR1으로 progress 요청)
print("\n=== 진행 상황 모니터링 ===")
for i in range(60):  # 최대 30분 대기
    time.sleep(30)
    # SIGUSR1 보내서 progress 강제 출력
    run_bg(f'sudo kill -USR1 $(pgrep -x dd) 2>/dev/null || true')
    time.sleep(1)
    log = run('tail -3 /home/tyranno/dd_progress.log 2>/dev/null', timeout=10)

    # dd 완료 여부 확인
    done = run('pgrep -x dd > /dev/null 2>&1 && echo running || echo done', timeout=5)
    if done == 'done':
        print("\n=== 복제 완료! ===")
        run('tail -5 /home/tyranno/dd_progress.log')
        break
    else:
        print(f"  [{(i+1)*30}s] 진행 중...")

ssh.close()
