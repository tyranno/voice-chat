# NanoPi 마이그레이션 - 회사 작업 목록

> 작성: 2026-05-12  
> 집 작업 완료 후 회사에서 이어서 진행

---

## 현재 상태 (집에서 완료)

| 항목 | 상태 | 비고 |
|------|------|------|
| voicechat-server 설치 | ✅ 완료 | systemd 서비스로 실행 중 |
| GCP 데이터 복원 | ✅ 완료 | /opt/voicechat/ |
| Cloudflare Tunnel (HTTP) | ✅ 완료 | https://voicechat.tyranno.xyz → NanoPi:8090 |
| Cloudflare Tunnel (SSH) | ✅ 완료 | ssh.tyranno.xyz → NanoPi:22 |
| Bridge LAN 설정 | ✅ 완료 | 192.168.123.200:9090 |

**NanoPi 접속 정보:**
- IP: 192.168.123.200
- User: tyranno / 1234
- SSH (외부): `ssh nanopi` (cloudflared ProxyCommand)
- SSH (LAN): `ssh nanopi-lan`

---

## 회사 PC 준비 (처음 한 번만)

### 1. cloudflared 설치
```powershell
winget install Cloudflare.cloudflared
```

### 2. SSH config 추가
`C:\Users\<사용자>\.ssh\config` 파일에 추가:
```
Host nanopi
  HostName ssh.tyranno.xyz
  User tyranno
  ProxyCommand cloudflared access ssh --hostname ssh.tyranno.xyz

Host nanopi-lan
  HostName 192.168.123.200
  User tyranno
```

### 3. SSH 접속 테스트
```bash
ssh nanopi
# 비밀번호: 1234
```

---

## 회사에서 할 작업

### Task 1: NanoPi에 개발 도구 설치
NanoPi SSH 접속 후:
```bash
# Node.js 22 (nvm)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
source ~/.bashrc
nvm install 22
nvm use 22
node --version

# 기타 도구
sudo apt-get install -y git ffmpeg yt-dlp
```

### Task 2: openclaw 설치 (NanoPi)
```bash
npm install -g openclaw
openclaw --version

# bridge service 설정
mkdir -p ~/.openclaw
# service-config.txt 설정 필요 (아래 참고)
```

openclaw service-config.txt 내용:
```
BRIDGE_ENABLED=true
BRIDGE_SERVER=localhost:9090   # 같은 서버니까 localhost
BRIDGE_TOKEN=oqcAeiu3fkPF9hmSJjnN1ELGMQgp7B05
BRIDGE_NAME=NanoPi 렉스
```

### Task 3: GCP에서 추가 데이터 마이그레이션
GCP 서버: `34.64.164.13` (SSH 접속 가능한지 확인 필요)

```bash
# GCP에서 NanoPi로 직접 복사 (NanoPi에서 실행)
rsync -avz ubuntu@34.64.164.13:/home/ubuntu/voicechat/ /opt/voicechat/

# 또는 GCP에서:
rsync -avz /home/ubuntu/voicechat/ tyranno@192.168.123.200:/opt/voicechat/
```

확인할 데이터:
- [ ] 음악 캐시 / 다운로드 파일
- [ ] 대화 기록 (DB 파일)
- [ ] 설정 파일 (.env 차이 없는지)
- [ ] cron 작업 (복권 등)

### Task 4: STT (VOSK) 설치
현재 NanoPi에 VOSK 없음 → STT 기능 안 됨

```bash
pip3 install vosk
# 한국어 모델 다운로드
wget https://alphacephei.com/vosk/models/vosk-model-small-ko-0.22.zip
unzip vosk-model-small-ko-0.22.zip -d ~/vosk-model
# vosk 서버 실행 설정 필요
```

### Task 5: nginx 설치 (선택)
여러 서비스 경로 분기 필요 시:
```bash
sudo apt-get install -y nginx
```

### Task 6: 전체 기능 검증
- [ ] 채팅 API: `curl https://voicechat.tyranno.xyz/health`
- [ ] STT 스트리밍
- [ ] 음악 검색/재생
- [ ] 복권 cron
- [ ] FCM 푸시 알림
- [ ] openclaw bridge 연결

### Task 7: GCP 종료
모든 검증 완료 후:
1. GCP 콘솔 → VM 인스턴스 중지
2. 스냅샷 하나 찍어두기 (혹시 몰라)
3. 한 달 후 완전 삭제

---

## 참고: 주요 파일 위치 (NanoPi)

```
/opt/voicechat/           - 서버 바이너리 + 데이터
/opt/voicechat/.env       - 환경변수
/etc/systemd/system/voicechat.service  - 서비스 설정
/etc/cloudflared/config.yml            - 터널 설정
/home/tyranno/.cloudflared/            - 인증서
```

## 참고: 주요 명령어

```bash
sudo systemctl status voicechat       # 서버 상태
sudo systemctl restart voicechat      # 서버 재시작
sudo journalctl -u voicechat -f       # 실시간 로그
sudo systemctl status cloudflared     # 터널 상태
```
