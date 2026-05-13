import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('192.168.123.200', username='tyranno', password='1234', timeout=10)

def run(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    print(stdout.read().decode(), end='')

run('lsblk -o NAME,SIZE,TYPE,MOUNTPOINT,FSTYPE,LABEL')
print()
run('sudo fdisk -l 2>/dev/null | grep "^Disk /dev/mmcblk"')

ssh.close()
