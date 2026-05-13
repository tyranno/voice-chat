# NanoPi 마이그레이션 - 작업 목록

> 작성: 2026-05-12, 갱신: 2026-05-13
> 집 작업 완료 후 회사에서 이어서 진행

---

## ⚠️⚠️ 긴급: NanoPi 먹통 상태 (2026-05-13) ⚠️⚠️

**현재 NanoPi가 hang 됨. 원격 복구 불가. 집에서 물리적 조치 필요.**

### 원인
- 128G SD카드(`/dev/mmcblk0`)가 쓰기 I/O 에러 (`error -110 timeout`, `Input/output error during write`)
- 커널 스레드 `[mmcqd/0]`이 계속 SD 에러 재시도 → 70% CPU → 결국 mmc 서브시스템 데드락 → 시스템 hang
- cloudflared가 `Restart=on-failure`인데도 안 돌아옴 = 시스템 자체 먹통
- 결과: `voicechat.tyranno.xyz` HTTP "error 1033", `ssh nanopi` "websocket: bad handshake"

### 집에서 할 일 (순서 중요)
1. **NanoPi 전원 뽑기 → 10초 → 다시 꽂기** (강제 재부팅)
2. **죽은 128G SD카드 슬롯에서 빼기** ← 핵심. 안 빼면 또 hang
3. 부팅되면 cloudflared + voicechat 자동 시작 → `ssh nanopi` 다시 됨
4. SD카드는 PC에서 별도 점검 (f3probe / H2testw — 진짜 불량인지 슬롯 문제인지)
5. 그 다음 아래 "회사에서 할 작업" Task 1~7 진행 (eMMC에, SD 없이)

### 회사 PC 상태 (2026-05-13 기준 완료됨)
- ✅ `winget install Cloudflare.cloudflared` 완료 (`C:\Program Files (x86)\cloudflared\cloudflared.exe`)
- ✅ `C:\Users\lab\.ssh\config`에 nanopi/nanopi-lan 항목 추가됨
- ✅ `C:\cygwin\home\lab\.ssh\config`에도 추가 (cygwin용)
- ✅ **SSH 공개키 인증 설정 완료** — `~/.ssh/id_rsa` 키가 NanoPi의 `/home/tyranno/.ssh/authorized_keys`에 등록됨. 비번 없이 `ssh nanopi` 됨 (어떤 툴에서든)

### NanoPi에서 이미 한 작업 (2026-05-13, hang 전)
- ✅ yt-dlp standalone 바이너리 설치 (`/usr/local/bin/yt-dlp`, aarch64). 기존 apt 버전(Python 3.6 의존 → 크래시)은 `/usr/local/bin/yt-dlp.py-backup`으로 백업
- ✅ systemd voicechat.service에 `PrivateTmp=true` 추가 (PyInstaller temp dir 문제 해결)
- ✅ `/opt/voicechat/data/cache` 디렉토리 생성
- ✅ **음악 검색/재생 정상 동작 확인** (NanoPi 주거용 IP라 YouTube 봇 차단 없음 — GCP는 봇 차단 당해서 음악 안 됐었음)
- ⚠️ journald 로그 캡(`SystemMaxUse=100M`) + nvm 설치 시도 중 NanoPi hang됨 → 미완료

---

## NanoPi 접속 정보
- IP: 192.168.123.200 (집 LAN)
- User: tyranno / 비번 1234 (sudo도 1234)
- SSH (외부): `ssh nanopi` ← **이제 키 인증, 비번 불필요**
- SSH (LAN, 집에서만): `ssh nanopi-lan`
- 만약 키 인증 안 되면: `SSH_ASKPASS` 방식 또는 cmd창에서 비번 직접

## SSH config (이미 설정됨, 참고용)
`C:\Users\lab\.ssh\config`:
```
Host nanopi
  HostName ssh.tyranno.xyz
  User tyranno
  ProxyCommand "C:\Program Files (x86)\cloudflared\cloudflared.exe" access ssh --hostname ssh.tyranno.xyz
Host nanopi-lan
  HostName 192.168.123.200
  User tyranno
```
cygwin은 `C:\cygwin\home\lab\.ssh\config` (ProxyCommand 경로만 `/cygdrive/c/Program Files (x86)/cloudflared/cloudflared.exe`로)

---

## 할 작업 (NanoPi 복구 후)

### Task 0: ⚠️ NanoPi 물리적 복구 (집에서, 최우선)
1. 전원 뽑기 → 10초 → 다시 꽂기
2. **죽은 128G SD카드 빼기** (안 빼면 또 hang)
3. 부팅 후 `ssh nanopi` 되는지 확인 (키 인증, 비번 불필요)
4. `systemctl is-active voicechat cloudflared` → 둘 다 active 확인
5. `curl https://voicechat.tyranno.xyz/health` → `{"status":"ok"}` 확인

### Task 0.5: SD카드 점검 (PC에서, 별도)
- 죽은 128G SD를 PC에 꽂아서:
  - Windows: **H2testw** 돌려서 실제 용량 검증
  - Linux/git-bash: `f3probe --destructive --time-ops /dev/sdX` (f3 패키지)
- 진짜 불량이면 → 폐기, 환불 요구
- 멀쩡한데 NanoPi 슬롯에서만 문제면 → USB3 메모리로 대체 (NanoPi M4 USB3 있음, `/dev/sda`로 잡힘)
- 검증된 카드/USB면 → NanoPi에 다시 끼우고 `/mnt/sdcard`에 ext4 마운트 + `/home/tyranno` bind (선택)
- **SD/USB 없어도 됨**: eMMC 3.6G면 Node+openclaw+VOSK(~500MB) 충분. 서버는 음악 파일 디스크에 안 쌓음

### Task 1: NanoPi에 개발 도구 설치 (eMMC, SD 없이)
NanoPi SSH 접속 후:
```bash
# journald 로그 캡 (미래 안전)
sudo bash -c 'mkdir -p /etc/systemd/journald.conf.d && printf "[Journal]\nSystemMaxUse=100M\nSystemMaxFileSize=20M\n" > /etc/systemd/journald.conf.d/00-size-limit.conf && systemctl restart systemd-journald && journalctl --vacuum-size=100M'

# Node.js 22 (nvm) — ~/.nvm에 설치 (eMMC)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
export NVM_DIR="$HOME/.nvm"; [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
nvm install 22 && nvm alias default 22
node --version  # v22.x 확인

# 기타: git/ffmpeg는 이미 설치됨. yt-dlp는 standalone 바이너리로 이미 교체됨 (apt 버전 X)
# ⚠️ "sudo apt-get install yt-dlp" 하지 말 것 — Python 3.6 버전이라 크래시함
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
현재 NanoPi에 VOSK 없음 → STT 기능 안 됨. `.env`의 `VOSK_URL` 확인 필요.

```bash
pip3 install vosk   # ⚠️ NanoPi는 Python 3.6 — vosk가 3.6 지원하는지 확인. 안 되면 nvm node로 vosk-browser 대안 또는 docker
# 한국어 모델 다운로드 (~50MB)
cd ~ && wget https://alphacephei.com/vosk/models/vosk-model-small-ko-0.22.zip
unzip vosk-model-small-ko-0.22.zip && mv vosk-model-small-ko-0.22 vosk-model-ko
# vosk 서버 실행 스크립트 + .env의 VOSK_URL=ws://localhost:포트 설정 + systemd 등록
```
⚠️ Python 3.6 제약 주의 — vosk 최신 버전이 3.6 안 되면: (a) `pip3 install 'vosk==0.3.32'` 같은 구버전, (b) Node 기반 STT, (c) 그냥 STT는 나중에. 음성 입력은 Web Speech API로도 폴백 가능 (앱 설정에서 STT 엔진 변경)

### Task 5: nginx 설치 (선택)
여러 서비스 경로 분기 필요 시:
```bash
sudo apt-get install -y nginx
```

### Task 6: 전체 기능 검증
- [x] 채팅 API: `curl https://voicechat.tyranno.xyz/health` → OK (hang 전 확인됨)
- [x] 음악 검색/재생 → OK (yt-dlp standalone + PrivateTmp fix 후. 주거용 IP라 봇 차단 없음)
- [ ] STT 스트리밍 (VOSK 설치 후)
- [ ] 복권 cron (GCP에 crontab 있었으면 NanoPi로 옮겨야 함 — `crontab -l`로 확인)
- [ ] FCM 푸시 알림 (`.env`의 `FCM_SERVICE_ACCOUNT` 경로 확인 — `/opt/voicechat/firebase-sa.json` 있음)
- [ ] openclaw bridge 연결 (`.env`의 `LOCAL_OPENCLAW_*` 설정 + openclaw 실행)
- [ ] 폰 앱에서 전체 기능 (채팅/음성/음악/저장/Ralph)

### Task 7: GCP 종료
모든 검증 완료 후:
1. GCP 콘솔 → VM 인스턴스 **중지** (Stop) — 즉시 청구 차단
2. 스냅샷 하나 찍어두기 (혹시 몰라)
3. 한 달 후 완전 삭제 (Delete)
4. ⚠️ DNS: 현재 `voicechat.tyranno.xyz` → Cloudflare Tunnel CNAME. GCP 끄기 전에 Tunnel 잘 도는지 재확인. 만약 Tunnel 문제 생기면 임시로 A 레코드 → 34.64.164.13 (GCP, DNS only)로 폴백 가능 (GCP 살아있는 동안만)

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
