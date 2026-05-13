import paramiko, sys

# GCP server check
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

key = paramiko.RSAKey.from_private_key_file(r'C:\Users\tyranno\.ssh\voicechat-key')
ssh.connect('34.64.164.13', username='tyranno', pkey=key, timeout=10)

cmd = (
    'echo "=== /opt/voicechat/data size ===" && '
    'du -sh /opt/voicechat/data/ 2>/dev/null && '
    'echo "=== .env contents (keys masked) ===" && '
    'sudo cat /opt/voicechat/.env 2>/dev/null | sed "s/=.*/=***/" && '
    'echo "=== google_stt_server.py present ===" && '
    'ls -lh /opt/voicechat/google_stt_server.py 2>/dev/null && '
    'echo "=== services ===" && '
    'systemctl is-active voicechat-server google-stt 2>/dev/null'
)
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
e = stderr.read().decode()
if e:
    print('ERR:', e)
ssh.close()
