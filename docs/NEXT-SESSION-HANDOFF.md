# Next Session Handoff — NanoPi 자가호스팅 마이그레이션

작성: 2026-05-12
상태: GCP → NanoPi M4 자가호스팅 진행 중. Cloudflare DNS NS 변경 후 작업 중단.

## 현재 상황 요약

**왜 마이그레이션?**
- GCP 무료 트라이얼 2일 후 종료, 월 ~$22 (3만원) 청구 시작
- 자가호스팅(NanoPi M4 + Cloudflare Tunnel)으로 전환 → 영구 무료 (전기료 월 ~1000원만)

**진행 상황 체크리스트**:
- [x] Cloudflare 계정 가입
- [x] tyranno.xyz 도메인 Cloudflare에 추가 (`Connect a domain`)
- [x] voicechat A 레코드 추가 (34.64.164.13, DNS only)
- [x] hosting.co.kr에서 NS를 Cloudflare로 변경 (`arvind.ns.cloudflare.com`, `braelyn.ns.cloudflare.com`)
- [ ] **DNS 전파 확인** (~30분~24h)
- [ ] NanoPi M4 부팅 + SSH 접근
- [ ] 마이그레이션 패키지 NanoPi에 복사
- [ ] setup 스크립트 실행
- [ ] GCP 데이터 백업 → NanoPi 복원
- [ ] Cloudflare Tunnel 생성 + DNS 라우팅
- [ ] 검증 (음악 검색/재생/저장 모두)
- [ ] GCP 인스턴스 중지

## 마이그레이션 패키지 위치

`c:\Project\88.MyProject\voice-chat-server\migration\` 폴더에 다 있음:
- `voicechat-server-linux-arm64` — NanoPi M4용 Go 바이너리 (10MB)
- `nanopi-setup.sh` — 자동 설치 스크립트
- `cloudflare-tunnel.md` — Cloudflare Tunnel 설정 가이드
- `README.md` — 전체 마이그레이션 흐름

## 다음 세션에서 할 작업 (순서대로)

### 1. DNS 전파 확인 (5분)

```powershell
nslookup -type=ns tyranno.xyz
```

응답이 `*.ns.cloudflare.com`이면 전파 완료. 아니면 30분~1시간 후 재시도.

또는 https://www.whatsmydns.net 에서 `tyranno.xyz` NS 조회.

Cloudflare 대시보드에서도 "Active" 표시되면 완료.

### 2. NanoPi M4 부팅 + SSH (15분)

- OS 깔려 있으면 부팅만 → SSH 가능 상태 확인
- 없으면 Armbian Ubuntu 깔기:
  - https://www.armbian.com/nanopi-m4/
  - microSD 8GB+ 굽기 (balenaEtcher)
  - 부팅 → 초기 설정 → SSH 활성화
- 같은 wifi에 연결 + IP 알아내기
- PC에서 `ssh <user>@<NanoPi_IP>` 가능 확인

### 3. 마이그레이션 패키지 복사 (2분)

```powershell
scp -r c:\Project\88.MyProject\voice-chat-server\migration\ <user>@<NanoPi_IP>:~/voicechat-migration
```

### 4. setup 스크립트 실행 (5~10분)

```bash
ssh <user>@<NanoPi_IP>
cd ~/voicechat-migration
bash nanopi-setup.sh
```

자동 설치되는 것:
- python3, ffmpeg, ufw, jq
- yt-dlp (ARM64 최신)
- cloudflared
- voicechat 서비스 user
- /opt/voicechat/ 구조
- systemd unit (자동 재시작 설정)

### 5. GCP 데이터 백업 (10분)

PC에서:
```powershell
ssh -i C:\Users\lab\.ssh\voicechat-key tyranno@voicechat.tyranno.xyz "sudo tar czf /tmp/vc-data.tar.gz /opt/voicechat/.env /opt/voicechat/data /opt/voicechat/firebase-sa.json && sudo chown `$(whoami) /tmp/vc-data.tar.gz"
scp -i C:\Users\lab\.ssh\voicechat-key tyranno@voicechat.tyranno.xyz:/tmp/vc-data.tar.gz .
scp vc-data.tar.gz <user>@<NanoPi_IP>:~/
```

NanoPi:
```bash
sudo tar xzf ~/vc-data.tar.gz -C /
sudo chown -R voicechat:voicechat /opt/voicechat/data /opt/voicechat/.env /opt/voicechat/firebase-sa.json
sudo chmod 600 /opt/voicechat/.env
```

### 6. Cloudflare Tunnel 설정 (10분)

NanoPi에서:
```bash
cloudflared tunnel login
# 브라우저 URL 나옴 → PC에서 열어서 tyranno.xyz 인증

cloudflared tunnel create voicechat
# Tunnel UUID 발급. ~/.cloudflared/<UUID>.json 생성됨

cloudflared tunnel route dns voicechat voicechat.tyranno.xyz
# Cloudflare DNS에 CNAME 자동 추가
```

config.yml 작성:
```bash
mkdir -p ~/.cloudflared
nano ~/.cloudflared/config.yml
```

내용 (`<USER>`, `<UUID>` 본인 값으로 치환):
```yaml
tunnel: voicechat
credentials-file: /home/<USER>/.cloudflared/<UUID>.json

ingress:
  - hostname: voicechat.tyranno.xyz
    service: http://localhost:8090
    originRequest:
      noTLSVerify: true
      connectTimeout: 30s
      tlsTimeout: 30s
      keepAliveTimeout: 90s
      httpHostHeader: voicechat.tyranno.xyz
  - service: http_status:404
```

서비스 등록:
```bash
sudo cloudflared service install
sudo systemctl enable --now cloudflared
sudo systemctl start voicechat
sudo systemctl status voicechat cloudflared
```

### 7. 검증 (10분)

```bash
# 내부 (NanoPi에서 자체)
curl -v http://localhost:8090/api/youtube/search?q=test

# 외부 (PC/폰에서)
curl -v https://voicechat.tyranno.xyz/api/youtube/search?q=test
```

폰 앱:
- 음악 검색 50개 + 무한스크롤 동작
- 트랙 재생 (시간 표시 즉시, thumb 이동)
- 저장된 트랙 재생 (시간 정상)
- 다운로드 (16워커)
- 채팅 / 마이크 / 등 다른 기능

### 8. GCP 중지

검증 OK 며칠 후:
- GCP 콘솔 → 인스턴스 STOP (즉시 청구 차단)
- 일주일 모니터링 후 → DELETE

## 이번 세션에서 완료된 작업 (커밋 대상)

### 앱 측 (`c:\Project\88.MyProject\voice-chat`)

**v0.10.22 ~ v0.10.24 누적 fix들**:

1. **랜덤 크래시 fix** ([BackgroundAudioPlugin.java](android/app/src/main/java/com/tyranokim/voicechat/audio/BackgroundAudioPlugin.java))
   - `startService()`가 ACTION_PLAY일 때만 `startForegroundService` 사용
   - 다른 액션(PING/PAUSE/STOP/SEEK/RATE/RESUME/NEXT/PREV)은 plain `startService`
   - 원인: 모든 액션에 `startForegroundService` 쓰면 PING 같은 액션이 startForeground 안 부르고 종료 → Android 14+ `ForegroundServiceDidNotStartInTimeException`로 5초 후 앱 강제종료
   - 효과: 채팅/마이크/어디서나 무작위 크래시 해결

2. **저장된 트랙 duration 표시 fix**
   - JS 측에서 `t.durationMs`(listTracks의 MediaStore 값) 즉시 `bgDurationMs`에 박음 ([music/+page.svelte:147-150](src/routes/music/+page.svelte))
   - Native broadcast 무시하고 리스트 값을 source of truth로 사용
   - broadcast가 0 보내도 안 덮어쓰기 (`if (dur > 0)`)

3. **`<unknown>` artist fix** ([MusicLibraryPlugin.java](android/app/src/main/java/com/tyranokim/voicechat/downloader/MusicLibraryPlugin.java))
   - IS_PENDING=0 풀린 후 Android MediaScanner가 m4a 임베디드 태그 없으니까 TITLE/ARTIST를 `<unknown>`으로 덮어버림
   - Fix: 그 직후에 TITLE+ARTIST+DURATION 다시 update해서 덮어쓰기
   - UI 측: `<unknown>` → 'Rex'/파일명 fallback

4. **다운로드 워커 4 → 8 → 16개**
   - 더 많은 병렬 연결로 YouTube throttle 우회
   - read timeout 60s → 300s (YouTube 일시 침묵 대응)
   - 취소 버튼 (다운 중 💾 버튼 다시 누르면 cancel)

5. **검색 페이지네이션 (무한 스크롤)**
   - 첫 50곡 → 스크롤 끝까지 → 자동 50곡 추가 (IntersectionObserver)
   - 최대 200곡 (서버 yt-dlp ytsearch 한도)

6. **시간 포맷 H:MM:SS**
   - 1시간 미만: M:SS (예: 3:33)
   - 1시간 이상: H:MM:SS (예: 8:23:30) — 500분 mix 등

7. **개발자 모드 디버그 표시**
   - 컨트롤러 아래 `dur=XXX pos=XXX state=XXX bc=XXX since=Xs`
   - 저장 트랙 리스트 `ms=XXX MS=XXX MMR=XXX MP=XXX`

8. **스트리밍 duration 즉시 표시**
   - 클릭 시 `/api/youtube/stream` 호출해서 서버가 yt-dlp로 얻은 duration 받아 즉시 박음

### 서버 측 (`c:\Project\88.MyProject\voice-chat-server`)

1. **Proxy semaphore 5 → 16 → 32** ([youtube.go:36-40](youtube.go))
   - 5는 너무 빡빡해서 stale 연결 1개 + 4워커 다운로드 = 슬롯 부족 → 503
   - 32: 16워커 + streaming + stale + 여유

2. **검색 19 → 50개**
   - `ytsearch50:` yt-dlp 활용
   - 1시간 캐싱 → 같은 검색 즉시 응답

3. **검색 페이지네이션**
   - `/api/youtube/search?q=X&offset=N&limit=50`
   - 캐시 키: query별 최대 사이즈 저장. 다음 페이지 요청 시 더 많이 fetch

4. **`searchYouTubeWithSize(query, size)` 함수 추가**
   - offset+limit ≤ cache size면 캐시에서 응답
   - 아니면 yt-dlp로 더 큰 사이즈 재요청

### 마이그레이션 패키지 (`c:\Project\88.MyProject\voice-chat-server\migration\`)

- ARM64 바이너리 (10MB)
- setup 스크립트 (NanoPi 의존성 자동 설치)
- Cloudflare Tunnel 가이드
- README

## 미해결 / 검증 대기

다음 세션에서 검증 필요:
- [ ] v0.10.24 build 57: HH:MM:SS 시간 포맷 (1시간 이상 트랙)
- [ ] v0.10.24 build 55: 검색 무한 스크롤 (스크롤 끝까지 → 자동 50곡 추가)
- [ ] v0.10.24 build 56: 16워커 다운로드 속도 (이전 대비 2배?)
- [ ] 컨트롤러 시간 / thumb 이동 정상 (실 native broadcast 또는 ticker fallback)
- [ ] `<unknown>` artist 표시 fix (기존 트랙 → 'Rex' / 새 다운로드 → 정상 artist)

## 파일/위치 참조

| 항목 | 위치 |
|---|---|
| 앱 코드 | `c:\Project\88.MyProject\voice-chat` |
| 서버 코드 | `c:\Project\88.MyProject\voice-chat-server` |
| 마이그레이션 패키지 | `c:\Project\88.MyProject\voice-chat-server\migration\` |
| SSH 키 (GCP 접속) | `C:\Users\lab\.ssh\voicechat-key` |
| 도메인 | `tyranno.xyz` (hosting.co.kr 등록기관, Cloudflare DNS) |
| Cloudflare NS | `arvind.ns.cloudflare.com`, `braelyn.ns.cloudflare.com` |
| 현재 GCP IP | `34.64.164.13` (Seoul, e2-micro) |
| 현재 APK | v0.10.24 build 57, 9.1MB |
| APK 배포 URL | https://voicechat.tyranno.xyz/api/apk/download |
| 디버그 keystore | `C:\Users\lab\.android\debug.keystore` |
| Java | `C:\Program Files\Android\openjdk\jdk-21.0.8` |
| Android SDK | `C:\Program Files (x86)\Android\android-sdk` |

## 빌드 환경 환경변수

```powershell
$env:JAVA_HOME = "C:\Program Files\Android\openjdk\jdk-21.0.8"
$env:ANDROID_HOME = "C:\Program Files (x86)\Android\android-sdk"
$env:ANDROID_SDK_ROOT = "C:\Program Files (x86)\Android\android-sdk"
$env:PATH = "$env:JAVA_HOME\bin;$env:PATH"
```

## 다음 세션 빠른 시작 명령

```
# 진행 상황 확인
nslookup -type=ns tyranno.xyz   # cloudflare.com이면 전파 완료
curl https://voicechat.tyranno.xyz/api/apk/latest   # 서버 응답 확인

# NanoPi 마이그레이션 시작
# (NanoPi IP 알려주면 원격 진행 가능)
```
