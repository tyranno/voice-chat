import subprocess, sys

SECTOR = 8192

result = subprocess.run(
    ['sudo', 'dd', 'if=/dev/sda', 'bs=512', 'skip={}'.format(SECTOR), 'count=8'],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE
)
data = bytearray(result.stdout)
print(f'Read {len(data)} bytes')

text_start = data.find(b'FIRMWARE_VER')
if text_start < 0:
    print('ERROR: FIRMWARE_VER not found!')
    sys.exit(1)

for line in bytes(data[text_start:]).split(b'\n'):
    if b'CMDLINE' in line:
        print('Before:', line.decode(errors='replace'))
        break

count = bytes(data).count(b'mmcblk1')
new_data = bytearray(bytes(data).replace(b'mmcblk1', b'mmcblk0'))
print(f'Replaced {count} occurrences mmcblk1 -> mmcblk0')

for line in bytes(new_data[text_start:]).split(b'\n'):
    if b'CMDLINE' in line:
        print('After: ', line.decode(errors='replace'))
        break

proc = subprocess.run(
    ['sudo', 'dd', 'of=/dev/sda', 'bs=512', 'seek={}'.format(SECTOR), 'count=8'],
    input=bytes(new_data),
    stdout=subprocess.PIPE, stderr=subprocess.PIPE
)
print('Write rc:', proc.returncode, proc.stderr.decode().strip())
print('DONE')
