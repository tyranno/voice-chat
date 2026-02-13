# VoiceChat 아키텍처

## 전체 구조

```
┌──────────────┐    HTTPS (443)     ┌──────────────────┐    TLS/TCP (9090)    ┌──────────────┐         ┌──────────┐
│   App        │ ──────────────────→│  GCP Server      │←────────────────────│  ClawBridge  │────────→│ OpenClaw │
│ (SvelteKit)  │   REST API         │ (Go, voicechat)  │   Bridge Protocol   │   (Go)       │  stdin  │  (Agent) │
│ + Capacitor  │   SSE streaming    │                  │   길이+JSON          │              │  stdout │          │
└──────────────┘                    └──────────────────┘                     └──────────────┘         └──────────┘
     안드로이드/웹                     34.64.164.13                            회사 PC (SYSTEM)
```

## 3개 프로젝트 (각각 별도 Git)

### 1. App (`tyranno/voice-chat`)
- **경로**: `C:\Project\88.MyProject\voice-chat`
- **스택**: SvelteKit 5 + Capacitor 8 + Tailwind 4 + adapter-static
- **통신**: HTTPS로 GCP 서버 직접 호출 (서버 라우트 없음, 클라이언트 전용)
- **설정**: localStorage에 서버 URL 저장 (`voicechat-settings`)
- **엔드포인트 사용**:
  - `GET /health` — 연결 테스트
  - `GET /api/instances` — Bridge 목록 조회
  - `POST /api/chat` — 채팅 (SSE 스트리밍 응답)
- **STT**: WebView에서 Web Speech API 미지원 → `@capacitor-community/speech-recognition` 네이티브 플러그인
- **빌드**: `npm run build` → `npx cap sync android` → WSL Gradle `assembleDebug`

### 2. GCP Server (`tyranno/voice-chat-server`)
- **경로**: `C:\Project\88.MyProject\voice-chat-server`
- **배포**: GCP VM `34.64.164.13`
- **바이너리**: `/opt/voicechat/voicechat-server`
- **서비스**: `voicechat.service` (systemd, root)
- **설정**: `/opt/voicechat/.env`
- **포트**:
  - **443 (HTTPS)**: 앱 API — 직접 TLS (Let's Encrypt 인증서)
  - **9090 (TCP)**: Bridge 연결 수신 — TLS 암호화
- **인증**:
  - 앱 → 서버: Access Code (헤더)
  - Bridge → 서버: Bridge Token (등록 시)
- **소스 파일**:
  - `main.go` — 서버 시작, 시그널 처리
  - `config.go` — 환경변수 기반 설정
  - `api.go` — HTTP API (health, instances, chat)
  - `bridge.go` — Bridge TCP 서버, 연결 관리
  - `relay.go` — 앱 ↔ Bridge 메시지 중계
  - `protocol.go` — TCP 프로토콜 (4바이트 길이 헤더 + JSON)
  - `auth.go` — 인증

### 3. ClawBridge (`tyranno/clawdbot-service` 내 bridge.go)
- **경로**: clawdbot-service 프로젝트에 포함
- **역할**: GCP 서버에 TLS/TCP 상시 연결, OpenClaw와 채팅 중계
- **설정**: `service-config.txt` (BRIDGE_SERVER, BRIDGE_TOKEN, BRIDGE_NAME)
- **프로토콜**: 4바이트 길이 헤더 + JSON (register → heartbeat → chat_request/response)
- **이름 등록**: `BRIDGE_NAME`으로 서버에 등록 (예: "회사 렉스")
- **앱에서**: 등록된 이름을 편집/변경하여 사용 (별도 기기 등록 플로우 없음)

## 통신 프로토콜

### App ↔ Server (HTTPS)
```
App → GET  /health              → { status, instances, timestamp }
App → GET  /api/instances       → [{ id, name, status, connectedAt }]
App → POST /api/chat            → SSE stream (delta chunks + [DONE])
      Body: { instanceId, messages: [{ role, content }] }
```

### Server ↔ Bridge (TLS/TCP, 포트 9090)
```
Bridge → register   { type, name, token }
Bridge ↔ heartbeat  { type: "heartbeat" }
Server → chat_request   { type, requestId, messages }
Bridge → chat_response  { type, requestId, delta, done }
Bridge → chat_error     { type, requestId, error }
```

메시지 포맷: `[4바이트 길이(Big Endian)][JSON 데이터]`

## 배포

### GCP 서버 배포
1. 로컬에서 Linux 바이너리 빌드 (Go 필요) 또는 서버에서 빌드
2. SCP로 `/opt/voicechat/voicechat-server` 업로드
3. `sudo systemctl restart voicechat`

### 앱 빌드
1. `npm run build` (SvelteKit → static)
2. `npx cap sync android`
3. WSL에서 `./gradlew assembleDebug`
4. APK: `android/app/build/outputs/apk/debug/app-debug.apk`

## SSH 접속
```bash
ssh tyranno@34.64.164.13 -i ~/.ssh/voicechat-key
```
SYSTEM 계정: `workspace/vc-key` 사용

## 알려진 이슈
- Bridge 60초 타임아웃 → heartbeat 처리 조사 필요
- nginx 80번 프록시 설정 존재하나 미사용 (서버가 직접 443 TLS)
