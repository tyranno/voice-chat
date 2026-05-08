# VoiceChat 시스템 개요 (통합)

> 작성일: 2026-05-08  
> 범위: Android 앱 + GCP 서버 + Windows Bridge + Python STT  
> 목적: 작업 계획의 기준이 되는 현재 시스템의 단일 진실 문서

---

## 0. 관련 저장소

| 저장소 | 경로 | 역할 |
|--------|------|------|
| **voice-chat** | `c:\Project\88.MyProject\voice-chat` | Android 앱 (SvelteKit + Capacitor) |
| **voice-chat-server** | `c:\Project\88.MyProject\voice-chat-server` | GCP VM의 Go 서버 |
| **clawdbot-service** | `c:\Project\88.MyProject\clawdbot-service` | Windows 서비스 (Bridge + OpenClaw 관리자) |
| OpenClaw Gateway | (별도) | Node.js, `:18789`, Anthropic Claude 호출 |
| google_stt_server.py | GCP `/opt/voicechat/` | Python WebSocket(`:2700`), Google Cloud STT |

---

## 1. 시스템 구성

```
┌──────────────────────────────────────────────────────────────────┐
│  [1] Samsung S25 — VoiceChat App (Capacitor + SvelteKit 5)      │
│                                                                  │
│  WebView (Svelte 5 runes)                                        │
│   └─ +page.svelte (메인 UI + 전체 로직)                           │
│      ├─ NativeSTT plugin → 마이크 캡처 + WebSocket               │
│      ├─ NativeAudio plugin → Android TTS                         │
│      ├─ BackgroundAudio plugin → ExoPlayer (백그라운드 음악)      │
│      ├─ FileDownloader plugin                                    │
│      └─ HTTPS / SSE / WSS                                        │
└──────────────────────────────────────────────────────────────────┘
                            │ 인터넷 (TLS)
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│  [2] GCP VM 34.64.164.13 — voicechat.tyranno.xyz                │
│                                                                  │
│  voice-chat-server (Go, systemd: voicechat-server)              │
│    HTTPS :443                                                    │
│      ├─ /health, /api/instances                                 │
│      ├─ /api/chat (SSE relay)                                   │
│      ├─ /api/stt/stream (WebSocket proxy)                       │
│      ├─ /api/tts (Google Cloud TTS)                             │
│      ├─ /api/conversations, /api/notify, /api/notifications/ws  │
│      ├─ /api/fcm/register, /api/fcm/push                        │
│      ├─ /api/files/upload, /api/files/:id/:name                 │
│      ├─ /api/apk/latest, /api/apk/download, /api/apk/upload     │
│      └─ /api/youtube/{search,stream,proxy,hls-proxy,hls-segment}│
│    TLS TCP :9090 (Bridge 연결)                                  │
│                                                                  │
│  google_stt_server.py (Python, systemd: google-stt)             │
│    ws://127.0.0.1:2700                                          │
│    VAD(RMS) → Google Cloud STT REST API                         │
└──────────────────────────────────────────────────────────────────┘
                            │ 인터넷 (TLS TCP :9090)
                            ▼
┌──────────────────────────────────────────────────────────────────┐
│  [3] 윈도우 PC — clawdbot-service.exe (Go, Windows Service)      │
│                                                                  │
│  서비스명: OpenClawGateway (자동 시작 + 실패 시 자동 재시작)      │
│   ├─ Bridge Client → TLS TCP :9090 → GCP                        │
│   ├─ chat_request 수신 → system prompt 주입 → OpenClaw 호출      │
│   ├─ chat_response (delta) 송신                                 │
│   ├─ [[FILE:...]] 마커 검출 → /api/files/upload → file_response │
│   ├─ Worktime 모니터, Power Monitor, ecount 등 (별개)           │
│   └─ OpenClaw Gateway 프로세스 관리 (node entry.js)             │
│                                                                  │
│  OpenClaw Gateway (Node.js)                                      │
│   ws://127.0.0.1:18789                                          │
│   ├─ POST /v1/chat/completions (OpenAI 호환, SSE)              │
│   ├─ Anthropic Claude 호출                                      │
│   ├─ Memory / Tools / Telegram Bot 공유                          │
│   └─ "user" 필드로 세션 분리 (voicechat-app)                    │
└──────────────────────────────────────────────────────────────────┘
```

---

## 2. 통신 채널 매트릭스

### 2.1 앱 → GCP 서버

| 경로 | 프로토콜 | 용도 | 코드 |
|------|----------|------|------|
| `/health` | HTTPS GET | 서버 헬스체크 | [src/lib/api/health.ts](../src/lib/api/health.ts) |
| `/api/instances` | HTTPS GET | 연결된 Bridge 목록 | [src/lib/api/instances.ts](../src/lib/api/instances.ts) |
| `/api/chat` | HTTPS POST + SSE | AI 대화 스트리밍 | [src/lib/api/openclaw.ts](../src/lib/api/openclaw.ts) |
| `/api/stt/stream` | WSS | STT 오디오 스트림 | NativeSttPlugin.java (OkHttp WS) |
| `/api/conversations(/:id)` | HTTPS GET/POST/PUT/DELETE | 대화 CRUD | [src/lib/api/conversations.ts](../src/lib/api/conversations.ts) |
| `/api/notify` | HTTPS POST | 외부 알림 발송 | [src/lib/api/notifications.ts](../src/lib/api/notifications.ts) |
| `/api/notifications/ws` | WSS | 실시간 알림 수신 (대안) | [src/lib/notifications/websocket.ts](../src/lib/notifications/websocket.ts) |
| `/api/fcm/register` | HTTPS POST | FCM 토큰 등록 | [src/lib/api/fcm.ts](../src/lib/api/fcm.ts) |
| `/api/files/upload` | HTTPS POST multipart | (Bridge 전용, 앱은 다운로드만) | — |
| `/api/files/:id/:name` | HTTPS GET | 파일 다운로드 | [src/lib/api/downloader.ts](../src/lib/api/downloader.ts) |
| `/api/apk/latest` | HTTPS GET | OTA 버전 체크 | [src/lib/api/updater.ts](../src/lib/api/updater.ts) |
| `/api/apk/download` | HTTPS GET | APK 다운로드 | (네이티브에서 처리) |
| `/api/youtube/search` | HTTPS GET | YouTube 검색 | [src/routes/+page.svelte](../src/routes/+page.svelte) |
| `/api/youtube/hls-proxy` | HTTPS GET | YouTube 라이브 HLS 프록시 | StreamUrlResolver.java |

### 2.2 GCP 서버 ↔ ClawBridge (TLS TCP :9090)

**Wire format**: `[4-byte BE length][JSON body]`

| Type | 방향 | 페이로드 | 정의 |
|------|------|----------|------|
| `register` | Bridge → Server | `name`, `token` | [protocol.go](../voice-chat-server/protocol.go) |
| `heartbeat` | 양방향 (30초) | (empty) | |
| `chat_request` | Server → Bridge | `requestId`, `messages[]`, `user` | |
| `chat_response` | Bridge → Server | `requestId`, `delta` 또는 `done:true` | |
| `chat_error` | Bridge → Server | `requestId`, `error` | |
| `file_response` | Bridge → Server | `requestId`, `filename`, `url`, `size`, `mimeType` | |

**최대 메시지 크기**: 10MB · **읽기 deadline**: 60초 · **재연결 백오프**: 5s → 60s (지수 증가, 30초 이상 유지 시 리셋)

### 2.3 GCP 서버 → 외부

| 대상 | 프로토콜 | 용도 |
|------|----------|------|
| `ws://127.0.0.1:2700` | WebSocket | google_stt_server.py |
| Google Cloud TTS API | HTTPS REST | TTS 음성 합성 (한국어 Neural2) |
| Google Cloud STT API | HTTPS REST | (Python 서버 내부) |
| FCM Server | HTTPS | 푸시 알림 발송 |

### 2.4 ClawBridge → OpenClaw Gateway

```
POST http://localhost:18789/v1/chat/completions
Headers:
  Content-Type: application/json
  x-openclaw-agent-id: main
  Authorization: Bearer <openclawToken> (optional)
Body:
  { model: "openclaw", stream: true, user: "voicechat-app", messages: [...] }
```

---

## 3. 핵심 데이터 흐름

### 3.1 음성 대화 (한 턴)

```
1. 사용자가 마이크에 발화
2. NativeSttPlugin.java
     AudioRecord(16kHz, mono, 16-bit) → OkHttp WSS → /api/stt/stream
3. voice-chat-server stt.go
     앱 ↔ google_stt_server.py 양방향 fan-out
     Vosk JSON → app JSON 변환: {partial} | {final, text} → {type, text}
4. NativeSTT(.ts) onFinal 콜백 → finalBuffer 누적
5. +page.svelte
     - 1000ms 디바운스 (FINAL_DEBOUNCE_MS)
     - barge-in: TTS 재생 중이면 stop()
     - sendMessage(text)
6. streamChat() — POST /api/chat (SSE, AbortController 5분 timeout)
     body: { instanceId, messages, conversationId }
7. voice-chat-server api.go handleChat
     → relay.go RelayChat(bridgeID, requestID, messages, user)
     → bridge.go BridgeManager.SendChatRequest (TCP)
8. clawdbot-service bridge.go handleChatRequest
     - voiceChatSystemPrompt 주입 (Rex 페르소나, [[FILE:...]] 마커 안내)
     - POST localhost:18789/v1/chat/completions (SSE)
     - OpenClaw → Anthropic Claude
9. SSE delta → chat_response (TCP, per-delta)
10. relay.go → SSE data: {"delta": "..."} → app
11. +page.svelte onDelta
     - messages[assistantIdx].content 누적
     - sentenceBuffer에 모아 문장 단위로 tts.addChunk()
12. CloudTTS (Android NativeAudio plugin)
     - 문장별 NativeAudio.speak()
     - Android TextToSpeech (USAGE_ASSISTANCE_NAVIGATION_GUIDANCE)
13. TTS onStart → STT pause (에코 방지)
14. TTS onEnd → STT resume + setListening
15. SSE [DONE] → onDone → fileUrls 추출 → persistMessages → pendingMessage flush
```

### 3.2 파일 전송 흐름

```
AI 응답 텍스트에 "[[FILE:C:\temp\report.txt]]" 포함
  ↓
clawdbot-service bridge.go uploadAndNotify()
  - 정규식 [[FILE:(.+?)]] 추출
  - multipart POST https://voicechat.tyranno.xyz/api/files/upload
  ↓
voice-chat-server (filed)
  - 파일 저장 (/opt/voicechat/data/...)
  - downloadUrl 반환
  ↓
file_response 메시지 (TCP)
  - Bridge → Server → SSE 별도 이벤트로 앱에 전달
  ↓
앱: messages[idx].downloads[] 추가 → 다운로드 버튼 표시
```

### 3.3 자동 인스턴스 복구 ([openclaw.ts](../src/lib/api/openclaw.ts))

```
서버 재시작 → Bridge ID 변경 → 앱이 옛 ID로 요청
  → 404 "Instance not found"
  → getInstances() 재조회
  → settings.selectedInstance = 첫 인스턴스
  → 재귀 1회 재시도 (MAX_RETRY_DEPTH=1)
```

---

## 4. 앱 내부 구조

### 4.1 진입점

```
src/app.html
  └─ +layout.svelte (전역 에러 배너)
       └─ +page.svelte ★ 메인 UI 1100줄+ (현재 단일 파일 집중)
            ├─ /music/+page.svelte
            ├─ /notifications/+page.svelte
            └─ /settings/+page.svelte
```

[+layout.ts](../src/routes/+layout.ts): `prerender=true, ssr=false` → SPA 모드, `adapter-static`

### 4.2 핵심 모듈

| 영역 | 파일 | 책임 |
|------|------|------|
| **상태** | [conversation.svelte.ts](../src/lib/stores/conversation.svelte.ts) | `idle/listening/processing/speaking` 머신 |
| | [settings.svelte.ts](../src/lib/stores/settings.svelte.ts) | localStorage 기반 설정 |
| | [conversations.svelte.ts](../src/lib/stores/conversations.svelte.ts) | 대화 메타 |
| | [musicHistory.svelte.ts](../src/lib/stores/musicHistory.svelte.ts) | 음악 재생/플레이리스트 |
| | [notifications.svelte.ts](../src/lib/stores/notifications.svelte.ts) | 알림 큐 |
| **STT** | [stt/native.ts](../src/lib/stt/native.ts) | NativeSttPlugin 래퍼 (Java가 자체 재시작 관리) |
| | [stt/webspeech.ts](../src/lib/stt/webspeech.ts) | Web Speech API 폴백 (브라우저용) |
| **TTS** | [tts/cloud.ts](../src/lib/tts/cloud.ts) | NativeAudio 래퍼 (실제로는 on-device Android TTS) |
| | [tts/capacitor.ts](../src/lib/tts/capacitor.ts) | (대안) Capacitor TTS |
| | [tts/webspeech.ts](../src/lib/tts/webspeech.ts) | SpeechSynthesis 폴백 |
| **API** | [api/openclaw.ts](../src/lib/api/openclaw.ts) | SSE 채팅 클라이언트 + 자동 복구 |
| | [api/conversations.ts](../src/lib/api/conversations.ts) | 대화 CRUD |
| | [api/instances.ts](../src/lib/api/instances.ts) | Bridge 목록 |
| | [api/health.ts](../src/lib/api/health.ts) | 헬스체크 |
| | [api/notifications.ts](../src/lib/api/notifications.ts) | FCM 알림 수신 |
| | [api/fcm.ts](../src/lib/api/fcm.ts) | FCM 등록 |
| | [api/downloader.ts](../src/lib/api/downloader.ts) | 파일 URL 추출 + 다운로드 |
| | [api/updater.ts](../src/lib/api/updater.ts) | OTA 자동 업데이트 |
| **오디오** | [audio/backgroundAudio.ts](../src/lib/audio/backgroundAudio.ts) | BackgroundAudio plugin (ExoPlayer) |
| | [audio/streamResolver.ts](../src/lib/audio/streamResolver.ts) | YouTube URL 변환 |

### 4.3 네이티브 플러그인 (Android)

| 플러그인 | 파일 | 책임 |
|---------|------|------|
| `NativeStt` | [NativeSttPlugin.java](../android/app/src/main/java/com/tyranokim/voicechat/stt/NativeSttPlugin.java) | OkHttp WSS + AudioRecord |
| `NativeAudio` | [NativeAudioPlugin.java](../android/app/src/main/java/com/tyranokim/voicechat/audio/NativeAudioPlugin.java) | Android TextToSpeech (DND 우회) |
| `BackgroundAudio` | [BackgroundAudioPlugin.java](../android/app/src/main/java/com/tyranokim/voicechat/audio/BackgroundAudioPlugin.java) | ExoPlayer + ForegroundService |
| `FileDownloader` | [FileDownloaderPlugin.java](../android/app/src/main/java/com/tyranokim/voicechat/downloader/FileDownloaderPlugin.java) | DownloadManager |

[MainActivity.java](../android/app/src/main/java/com/tyranokim/voicechat/MainActivity.java)에서 모두 등록. **FCM plugin은 google-services.json 부재로 주석 처리됨.**

### 4.4 onMount 라이프사이클 ([+page.svelte](../src/routes/+page.svelte))

```
1. hardwareBackPress 리스너 (네이티브 뒤로가기)
2. FCM 토큰 등록 (registerFcmToken)
3. FCM 알림 콜백 (onFcmNotification → tts.speak)
4. 대화 목록 로드 (listConversations + getMessages 첫 번째)
5. checkConnection
   - settings.isConfigured 체크
   - GET /health
   - GET /api/instances
   - savedInstance 존재 → connected, 없으면 select-instance
6. TTS 초기화 (Native: CloudTTS / Web: WebSpeechTTS)
7. STT 초기화 (Native: NativeSTT / Web: WebSpeechSTT)
8. micGuardian (5초 인터벌, STT dead 감지 시 재시작)
9. waveform 애니메이션 (rAF)
10. connected + Native → 마이크 자동 ON
```

### 4.5 STT 가드 메커니즘 (분산되어 있음)

| 위치 | 동작 |
|------|------|
| `NativeSttPlugin.java` | Java가 자체 자동재시작 (1500ms), ERROR_NO_MATCH/ERROR_SPEECH_TIMEOUT 처리 |
| `NativeSTT.ts` | `_paused`, `_started`, `_isListening` 플래그 + listenerHandle 1회 등록 |
| `+page.svelte` micGuardian | 5초마다 STT dead 감지 → restart |
| `+page.svelte` onEnd 콜백 | WebSpeech 전용: 300ms 후 재시작 |

---

## 5. 상태 머신

```
            ┌──────┐  micEnabled=false
            │ idle │◄──────────────┐
            └──┬───┘                │
               │ micEnabled=true    │ stop/error
               ▼                    │
          ┌─────────┐               │
          │listening│               │
          └────┬────┘               │
       send    │                    │
               ▼                    │
          ┌──────────┐              │
          │processing│              │
          └────┬─────┘              │
       delta   │                    │
               ▼                    │
          ┌────────┐                │
          │speaking│                │
          └────┬───┘                │
        TTS    │ end                │
        끝     ▼                    │
       (mic on?yes→listening / no→idle) ─────────────────┘
```

**룰**: `micEnabled=true`일 때 `setIdle()` 호출되어도 자동으로 `listening`으로 전환됨.

---

## 6. 외부 의존성 / 인프라

### 6.1 GCP VM
- **VM**: `34.64.164.13`, 도메인 `voicechat.tyranno.xyz`
- **TLS**: Let's Encrypt (`/etc/letsencrypt/live/voicechat.tyranno.xyz/`)
- **systemd 서비스**:
  - `voicechat-server.service` (Go 바이너리, `/opt/voicechat/voicechat-server`)
  - `google-stt.service` (Python, `/opt/voicechat/google_stt_server.py`)
- **데이터**: `/opt/voicechat/data/` (대화, 파일, APK, FCM 등록)
- **메모리 제한**: `MEMORY_LIMIT_MB` 환경변수 (default 600MB, debug.SetMemoryLimit)

### 6.2 Windows PC
- **서비스**: `OpenClawGateway` (자동 시작 + 5/10/30초 단계 자동 재시작)
- **설정**: `~/.openclaw/service-config.txt`
- **로그**: `~/.openclaw/logs/service.log`
- **NSIS 인스톨러**: `clawdbot-service/installer/`

### 6.3 외부 API
- Google Cloud STT (REST)
- Google Cloud TTS (REST, Neural2)
- Anthropic Claude (OpenClaw 경유)
- YouTube (검색, HLS)
- FCM (옵셔널)

---

## 7. 배포 흐름

### 7.1 앱 빌드/배포

```powershell
# 1. SvelteKit 빌드
npm run build               # → build/

# 2. Capacitor 동기화
npx cap sync android        # → android/app/src/main/assets/public

# 3. Gradle 빌드
cd android
./gradlew assembleDebug
# 결과: android/app/build/outputs/apk/debug/app-debug.apk

# 4. 기기 설치
adb -s R3CY10AF61Z install -r android/app/build/outputs/apk/debug/app-debug.apk
```

또는 [build-apk.bat](../build-apk.bat), [deploy-apk.ps1](../deploy-apk.ps1) 활용.  
**OTA**: `/api/apk/upload`로 업로드 시 [updater.ts](../src/lib/api/updater.ts)가 `/api/apk/latest` 폴링하여 자동 업데이트.

### 7.2 GCP 서버 배포

```bat
cd c:\Project\88.MyProject\voice-chat-server
build-linux.bat            # 리눅스 바이너리 크로스빌드
deploy.bat                 # SCP 업로드 + systemctl restart
```

### 7.3 Windows 서비스 배포

```bat
cd c:\Project\88.MyProject\clawdbot-service
build-and-restart.bat      # 빌드 + 서비스 재시작
```

---

## 8. 알려진 이슈 / 작업 후보

### 8.1 코드 구조

- **[+page.svelte](../src/routes/+page.svelte) 1100줄+**: 메인 UI, 음악 플레이어, 대화 사이드바, STT/TTS 콜백, FCM, 알림이 모두 한 파일
  - 잠재 작업: 컴포넌트 분리 (`<MessageList>`, `<ConversationSidebar>`, `<MusicPlayer>`, `<MicButton>`, `<DebugPanel>`)
  - 잠재 작업: VoiceController 클래스로 STT/TTS 생명주기 통합 ([REFACTOR_PLAN.md](../REFACTOR_PLAN.md) 참고하되 현재 STT 라이브러리에 맞게 갱신 필요)

- **STT 가드 분산**: Java 자동재시작 + JS micGuardian + WebSpeech onEnd 재시작이 서로 다른 파일에 흩어짐
  - 잠재 작업: 단일 책임자에게 일임 (Java 또는 JS)

### 8.2 문서 동기화

- [docs/PLAN.md](PLAN.md): Deepgram/ElevenLabs 시절 원안 → 현재 Google STT/Android TTS와 불일치
- [ARCHITECTURE.md](../ARCHITECTURE.md): 경로가 `E:\Project\My\...` (실제: `c:\Project\88.MyProject\...`)
- [REFACTOR_PLAN.md](../REFACTOR_PLAN.md): `@capgo/capacitor-speech-recognition` 기반 분석 → 현재는 자체 NativeSttPlugin (OkHttp WSS)
- [voice-chat-server/ARCHITECTURE.md](../voice-chat-server/ARCHITECTURE.md): 동일하게 경로 outdated

### 8.3 운영/UX

- **Bridge 끊김 시 사용자 알림 부재**: 자동 복구되지만 토스트나 인디케이터 없음
- **Relay timeout 2분 hardcoded**: [relay.go:55](../voice-chat-server/relay.go) — 긴 응답 시 잘림 가능
- **앱 SSE timeout 5분**: [openclaw.ts:20](../src/lib/api/openclaw.ts) — 일치하지 않음
- **OpenClaw 단일 장애점**: 윈도우 PC가 꺼져있으면 모든 대화 불가 (Bridge 다중화 미구현)
- **FCM 비활성**: `google-services.json` 부재로 [MainActivity.java:31](../android/app/src/main/java/com/tyranokim/voicechat/MainActivity.java) 주석 처리

### 8.4 보안

- **Bridge token**: 환경 변수 의존 (BRIDGE_TOKEN), 회전 자동화 없음
- **API 키 노출 방어**: 서버 측에서만 보유 (Google STT/TTS) — 양호
- **CORS**: `*` 와일드카드 ([api.go:99](../voice-chat-server/api.go))

### 8.5 관측성

- 앱: `addDebug()`로 in-memory 디버그 로그만 (debugLog 2KB 슬라이딩)
- 서버: `log.Printf` 기반 stdout → systemd journal
- Bridge: 동일
- 잠재 작업: requestId 기반 분산 트레이싱, 에러 집계

---

## 9. 빠른 트러블슈팅 체크리스트

| 증상 | 1차 확인 |
|------|----------|
| 앱이 "서버에 연결할 수 없습니다" | `curl https://voicechat.tyranno.xyz/health` |
| "연결된 인스턴스 없음" | `curl https://voicechat.tyranno.xyz/api/instances` → `[]`이면 Windows 서비스 점검 |
| 윈도우 서비스 죽음 | `sc query OpenClawGateway`, `~/.openclaw/logs/service.log` |
| 응답이 안 옴 (instance OK) | OpenClaw Gateway `:18789` 동작 확인 |
| STT가 안 됨 | `systemctl status google-stt` (GCP) |
| TTS 음소거됨 | Samsung AudioHardening 이슈 — `STREAM_MUSIC` mute 금지 (NativeAudioPlugin.java) |
| 백그라운드 음악 끊김 | ForegroundService 알림 권한 / 배터리 최적화 예외 |

---

## 10. Ralph Loop / Advisor 통합 (2026-05-08 추가)

### 10.1 Ralph Loop - 실체

**위치**: `C:\Users\lab\.claude\plugins\marketplaces\claude-plugins-official\plugins\ralph-loop\` (Anthropic 공식, 현재 미설치)

**핵심 동작**:
- Claude Code 세션 안에서 실행되는 슬래시 커맨드 `/ralph-loop`
- 상태 파일: `.claude/ralph-loop.local.md` (YAML frontmatter + prompt)
- **Stop hook**이 세션 종료를 가로채고 같은 prompt를 반복 주입
- 종료 조건: `--max-iterations N` 도달 또는 `<promise>X</promise>` 출력
- 외부 모니터링: `head -10 .claude/ralph-loop.local.md`로 iteration·상태 확인

**호출 시그니처**:
```
/ralph-loop <PROMPT> [--max-iterations N] [--completion-promise 'TEXT']
/cancel-ralph
```

**중요한 제약**:
- OpenClaw Gateway는 Claude Code가 아님 (Anthropic API 래퍼) → Ralph Loop을 직접 못 띄움
- 따라서 Bridge 또는 별도 컴포넌트가 Claude Code 세션을 띄워야 함

### 10.2 Advisor - Claude Code 기본 동작

**Advisor는 별도 플러그인이 아니라 Claude Code의 기본 패턴**:
- Claude Code 안에서 Agent 툴(subagent dispatch)을 통해 별도 Claude 인스턴스에게 자문/검토 의뢰
- 즉, "다른 시스템 프롬프트로 같은 컨텍스트를 검토하게 시키는" 표준 Claude Code 사용법
- 설치 불필요. 어떤 Claude Code 세션 안에서나 즉시 사용 가능

**voice-chat 통합 시 두 가지 호출 경로**:

| 경로 | 사용처 | 구현 |
|------|--------|------|
| **인라인** (Ralph 내부) | Ralph 작업 중 Claude가 스스로 Advisor 서브에이전트 dispatch | Ralph prompt에 "검토 후 진행"같은 지시 포함 |
| **독립** (메인 chat에서 호출) | 사용자가 chat 응답 보고 "다른 의견" 버튼 클릭 | OpenClaw `/v1/chat/completions`에 Advisor 시스템 프롬프트로 새 호출 |

**독립 경로는 subprocess 불필요** — 기존 chat 인프라 재사용:
```
voice-chat App: "다른 의견" 버튼
  POST /api/chat { mode:"advisor", messages:[원본 + 검토 요청] }
    ↓
voice-chat-server → Bridge → OpenClaw
  - bridge.go에서 mode="advisor"면 voiceChatSystemPrompt 대신 advisorSystemPrompt 주입
  - user 필드: "voicechat-advisor"로 메모리 격리
    ↓
일반 chat_response 흐름 그대로
```

### 10.3 통합 아키텍처 결정

**MVP (Phase 3): 옵션 A — Bridge subprocess**
```
voice-chat App
  POST /api/chat (또는 /api/task) { mode:"ralph", prompt, options }
    ↓
voice-chat-server: 새 메시지 타입 task_start로 라우팅
    ↓
clawdbot-service Bridge:
  - workdir: %USERPROFILE%\ralph-tasks\<taskId>\
  - exec:    claude --headless ...
                    /ralph-loop "<prompt>"
                    --max-iterations 30 --completion-promise "DONE"
  - subprocess stdout 파싱 → task_progress 메시지
  - subprocess 종료     → task_done 메시지
  - 산출물 (workdir 안의 파일) → 기존 [[FILE:...]] 마커 흐름 재사용
    ↓
voice-chat App: 작업 카드 UI에 진행상황·완료 알림
```

**선택 이유**:
- 실제 Ralph Loop 플러그인을 그대로 사용 → 동작 보장
- 빠르게 검증 가능 (1주 내)
- 실패 시 Phase 5에서 옵션 B(Agent SDK)로 마이그레이션 경로 명확

**Phase 5 상용화 시 옵션 B 마이그레이션**:
- claude-agent-sdk(Node)로 Bridge에 임베드
- subprocess 관리 부담 제거, 동시성·관측성·취소 처리 깔끔

**Phase 3 사전 검증 필요 항목**:
- `claude --headless` 의 stdout 포맷 (JSONL transcript? 텍스트?)
- iteration별 진행 메시지 구분 방법
- Windows 서비스 컨텍스트에서 `claude` CLI 권한·환경 변수 (HOME, PATH, 플러그인 경로)
- 동시 작업 N개 제한 (CPU/메모리/Anthropic 요청 한도)
- task workdir 정리 정책 (성공 시 보존? 만료 시 삭제?)
- ralph-loop 플러그인 설치/업데이트 자동화

### 10.4 새 메시지 타입 (Bridge protocol 확장)

```
task_start    : App  → Server → Bridge   { taskId, mode:"ralph"|"advisor", prompt, options }
task_progress : Bridge → Server → App    { taskId, iteration, message, progress? }
task_log      : Bridge → Server → App    { taskId, line }   (선택)
task_done     : Bridge → Server → App    { taskId, summary, artifacts:[{name,url}] }
task_error    : Bridge → Server → App    { taskId, error }
task_cancel   : App  → Server → Bridge   { taskId }
```

### 10.5 Phase 4 - Advisor UX 통합

**구현 정리** (10.2 기반):
- Bridge: `/api/chat` body의 `mode` 필드로 분기. `mode="advisor"`면 advisorSystemPrompt 주입 + user="voicechat-advisor"
- 메시지 흐름·SSE 포맷 모두 메인 chat과 동일 (앱 클라이언트 코드 변경 최소화)
- subprocess·workdir 등 Ralph 인프라 불필요

**앱 UX**:
- 메시지 카드 우측 상단 아이콘 → "다른 의견 받기"
- 누르면 같은 카드 아래에 advisor 응답 펼침 (대비 가능한 UI)
- Ralph 작업 완료 시 task_done에 advisor 의견 자동 첨부 옵션 (설정에서 ON/OFF)

**Advisor 시스템 프롬프트 골자(안)**:
> 당신은 비판적 자문자 Advisor입니다. 사용자의 메인 AI 응답에 대해
> 1) 빠진 관점, 2) 잠재 리스크, 3) 더 나은 대안, 4) 검증되지 않은 가정
> 만 짚으세요. 메인 응답을 반복하지 마세요.

---

## 11. 관련 문서

| 문서 | 역할 | 상태 |
|------|------|------|
| 본 문서 ([SYSTEM-OVERVIEW.md](SYSTEM-OVERVIEW.md)) | 통합 시스템 진실 문서 | ✅ 최신 (2026-05-08) |
| [ARCHITECTURE.md](../ARCHITECTURE.md) | 앱 + GCP 서버 (간략) | ⚠️ 경로 outdated |
| [voice-chat-server/ARCHITECTURE.md](../../voice-chat-server/ARCHITECTURE.md) | 서버 상세 | ⚠️ 경로 outdated |
| [docs/PLAN.md](PLAN.md) | 초기 기획 (Deepgram/ElevenLabs) | ❌ 폐기 대상 |
| [REFACTOR_PLAN.md](../REFACTOR_PLAN.md) | 구 STT 라이브러리 기반 리팩토링 분석 | ❌ 폐기 대상 |
| [SERVER-CHECK.md](../SERVER-CHECK.md) | 1회성 점검 스냅샷 | 📌 시점성 자료 |
| [TEST-SCENARIOS.md](../TEST-SCENARIOS.md) | (확인 필요) | — |
