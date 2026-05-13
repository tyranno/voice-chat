import paramiko, sys

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.123.200', username='tyranno', password='1234', timeout=10)

cmd = (
    'echo "=== /var breakdown ===" && '
    'du -sh /var/* 2>/dev/null | sort -rh | head -10 && '
    'echo "=== /home breakdown ===" && '
    'du -sh /home/* 2>/dev/null | sort -rh | head -10 && '
    'echo "=== apt cache ===" && '
    'du -sh /var/cache/apt/archives/ 2>/dev/null && '
    'echo "=== /opt ===" && '
    'ls -la /opt/ && '
    'echo "=== root files ===" && '
    'ls -lh / | grep -v "^total" | head -20'
)
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
err = stderr.read().decode()
if err:
    print('STDERR:', err, file=sys.stderr)
ssh.close()
