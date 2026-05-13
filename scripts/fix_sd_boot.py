import sys

DISK = r'\\.\PhysicalDrive3'
SECTOR = 8192
SECTOR_SIZE = 512

print(f'SD 카드 열기: {DISK}')
try:
    disk = open(DISK, 'r+b')
except PermissionError:
    print('오류: 관리자 권한으로 실행하세요')
    print('  방법: 이 스크립트를 마우스 오른쪽 클릭 -> 관리자 권한으로 실행')
    sys.exit(1)

disk.seek(SECTOR * SECTOR_SIZE)
data = bytearray(disk.read(8 * SECTOR_SIZE))

idx = data.find(b'FIRMWARE_VER')
if idx < 0:
    print('오류: parameter.txt를 찾을 수 없습니다 (올바른 SD 카드인지 확인)')
    disk.close()
    sys.exit(1)

print('\n[수정 전]')
for line in bytes(data[idx:]).split(b'\n'):
    if b'CMDLINE' in line:
        print(line.decode(errors='replace'))
        break

count = bytes(data).count(b'storagemedia=emmc')
if count == 0:
    print('\n이미 수정되어 있거나 storagemedia=emmc 가 없습니다')
    disk.close()
    sys.exit(0)

new_data = bytearray(bytes(data).replace(b'storagemedia=emmc', b'storagemedia=sd  '))

print('\n[수정 후]')
for line in bytes(new_data[idx:]).split(b'\n'):
    if b'CMDLINE' in line:
        print(line.decode(errors='replace'))
        break

disk.seek(SECTOR * SECTOR_SIZE)
disk.write(bytes(new_data))
disk.flush()
disk.close()

print('\n완료! SD 카드를 NanoPi microSD 슬롯에 꽂고 전원 켜세요.')
