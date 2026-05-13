import paramiko, sys

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
key = paramiko.RSAKey.from_private_key_file(r'C:\Users\tyranno\.ssh\voicechat-key')
ssh.connect('34.64.164.13', username='tyranno', pkey=key, timeout=10)

cmd = (
    'echo "=== service status ===" && '
    'systemctl status voicechat-server --no-pager -l 2>&1 | head -20 && '
    'echo "=== actual env (PORT, BRIDGE_PORT) ===" && '
    'sudo grep -E "^(PORT|BRIDGE_PORT|TLS_ENABLED|BRIDGE_TLS_ENABLED)=" /opt/voicechat/.env && '
    'echo "=== listening ports ===" && '
    'ss -tlnp 2>/dev/null | grep -E ":(443|8080|8090|9090)" && '
    'echo "=== full env ===" && '
    'sudo cat /opt/voicechat/.env'
)
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode())
ssh.close()
