import paramiko, sys

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.123.200', username='tyranno', password='1234', timeout=30)

# Run cleanup commands via sudo
cleanup_cmd = (
    'sudo apt-get clean -y 2>&1 && echo "APT CLEAN OK" && '
    'sudo journalctl --vacuum-size=50M 2>&1 && echo "JOURNAL OK" && '
    'sudo find /var/log -name "*.gz" -delete 2>/dev/null && '
    'sudo find /var/log -name "*.1" -delete 2>/dev/null && '
    'echo "LOGS OK" && '
    'df -h / && echo "DONE"'
)

# Need to run with sudo but no password prompt - check sudoers
stdin, stdout, stderr = ssh.exec_command('sudo -n true 2>&1 && echo "SUDO OK" || echo "SUDO NEEDS PASSWORD"')
out = stdout.read().decode().strip()
print('Sudo check:', out)

if 'NEEDS PASSWORD' in out:
    # Try with password via stdin
    stdin2, stdout2, stderr2 = ssh.exec_command('sudo -S apt-get clean -y', get_pty=True)
    stdin2.write('1234\n')
    stdin2.flush()
    print(stdout2.read().decode())
else:
    stdin, stdout, stderr = ssh.exec_command(cleanup_cmd)
    print(stdout.read().decode())
    e = stderr.read().decode()
    if e:
        print('ERR:', e)

ssh.close()
