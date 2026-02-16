# VoiceChat App 아키텍처

> 최종 업데이트: 2026-02-16

## 개요

VoiceChat은 음성 기반 AI 대화 앱입니다. Samsung S25에서 마이크로 말하면 음성인식(STT) → AI 응답 생성 → 음성합성(TTS)으로 대화합니다.

## 기술 스택

- **프론트엔드**: SvelteKit + Capacitor (Android)
- **서버**: Go (`voice-chat-server`) on GCP VM
- **STT**: Google Cloud STT (REST API via WebSocket proxy)
- **TTS**: Android TextToSpeech (on-device)
- **AI**: OpenClaw Gateway → Anthropic Claude (ClawBridge 경유)

## 전체 시스템 구성

```
Samsung S25 (VoiceChat App)
  │
  ├── 음성인식 (STT)
  │     AudioRecord → OkHttp WebSocket
  │       → wss://voicechat.tyranno.xyz/api/stt/stream
  │       → GCP 서버 stt.go (WebSocket proxy)
  │       → ws://127.0.0.1:2700 (google_stt_server.py)
  │       → Google Cloud STT REST API
  │       ← 인식 결과 JSON
  │
  ├── AI 대화 (Chat)
  │     POST https://voicechat.tyranno.xyz/api/chat (SSE)
  │       → GCP 서버 relay.go
  │       → TCP (TLS :9090) → ClawBridge (Windows PC)
  │       → clawdbot-service bridge.go
  │       → POST http://localhost:18789/v1/chat/completions
  │       → OpenClaw Gateway → Anthropic Claude
  │       ← SSE 스트리밍 응답
  │
  └── 음성합성 (TTS)
        AI 응답 텍스트 → Android TextToSpeech (on-device)
        USAGE_ASSISTANCE_NAVIGATION_GUIDANCE (Samsung DND 우회)
```

## 앱 내부 구조

### 파일 구조
```
src/
├── routes/
│   └── +page.svelte          # 메인 UI + 대화 로직
├── lib/
│   ├── api/
│   │   └── openclaw.ts       # /api/chat SSE 스트리밍 클라이언트
│   ├── stt/
│   │   ├── native.ts         # Android: NativeSttPlugin wrapper
│   │   └── webspeech.ts      # 웹 브라우저: Web Speech API
│   ├── tts/
│   │   ├── cloud.ts          # Android: NativeAudioPlugin wrapper (on-device TTS)
│   │   └── webspeech.ts      # 웹 브라우저: SpeechSynthesis API
│   ├── conversation.svelte.ts # 대화 상태 관리
│   └── settings.svelte.ts     # 설정
android/
├── app/src/main/java/com/tyranokim/voicechat/
│   ├── MainActivity.java
│   ├── audio/
│   │   └── NativeAudioPlugin.java    # TTS (Android TextToSpeech)
│   └── stt/
│       └── NativeSttPlugin.java      # STT (OkHttp WebSocket)
```

### 데이터 흐름

```
[마이크 ON] → toggleMic()
  → NativeSTT.start()
  → NativeSttPlugin.java: OkHttp WebSocket 연결
  → AudioRecord → 서버로 오디오 스트리밍
  → 서버에서 인식 결과 수신

인식 결과 → onFinal(text)
  → finalBuffer 축적
  → 1200ms 디바운스 → flushFinalBuffer()
  → sendMessage(text)

sendMessage(text)
  → streamChat() → /api/chat SSE
  → 응답 delta → TTS.addChunk()
  → TTS 시작 → STT.pause() (피드백 루프 방지)
  → TTS 종료 → STT.resume()
```

### STT (음성인식)

**Android (NativeSttPlugin.java)**:
- OkHttp WebSocket으로 `wss://voicechat.tyranno.xyz/api/stt/stream` 연결
- AudioRecord (16kHz, 16-bit, mono)로 마이크 캡처
- 바이너리 오디오 → WebSocket → 서버 → Google STT
- 인식 결과를 Capacitor 이벤트로 JS에 전달

**웹 (webspeech.ts)**:
- Web Speech API (`SpeechRecognition`) 사용

### TTS (음성합성)

**Android (NativeAudioPlugin.java)**:
- Android `TextToSpeech` 사용 (on-device, 네트워크 불필요)
- `USAGE_ASSISTANCE_NAVIGATION_GUIDANCE`로 AudioAttributes 설정
  - Samsung S25의 DND/VIBRATE 모드에서도 소리 출력
- **주의**: Samsung AudioHardening이 `setStreamVolume(STREAM_MUSIC)` 차단
  → STREAM_MUSIC을 절대 mute하면 안 됨

**웹 (webspeech.ts)**:
- Web Speech Synthesis API 사용

### Chat (AI 대화)

**openclaw.ts**:
- `POST /api/chat`으로 SSE 스트리밍 요청
- `AbortController` 타임아웃: 60초 (SSE 스트리밍 고려)
- 인스턴스 자동 복구: 서버 재시작으로 bridge ID 변경 시 자동 재연결
- 재귀 depth 제한으로 무한 루프 방지

## 서버 구성

### GCP VM (34.64.164.13 / voicechat.tyranno.xyz)

| 서비스 | 포트 | 역할 |
|--------|------|------|
| voice-chat-server | :443 (HTTPS) | API 서버 |
| voice-chat-server | :9090 (TLS TCP) | ClawBridge 연결 |
| google_stt_server.py | :2700 (localhost) | STT WebSocket |
| nginx | :80 | HTTP→proxy (미사용) |

**SSH 접속**:
```bash
ssh -i ~/.ssh/voicechat-key tyranno@34.64.164.13
```

**API 엔드포인트**:
| 경로 | 메서드 | 설명 |
|------|--------|------|
| `/health` | GET | 헬스체크 |
| `/api/instances` | GET | 연결된 bridge 목록 |
| `/api/chat` | POST | AI 대화 (SSE 스트리밍) |
| `/api/tts` | POST/GET | Google Cloud TTS (MP3) |
| `/api/stt/stream` | WebSocket | STT 프록시 |
| `/api/apk/latest` | GET | APK 버전 정보 |
| `/api/apk/download` | GET | APK 다운로드 |
| `/api/files/upload` | POST | 파일 업로드 |
| `/api/files/:id/:name` | GET | 파일 다운로드 |

### Windows PC (우리집)

| 서비스 | 역할 |
|--------|------|
| OpenClawGateway (Windows 서비스) | clawdbot-service.exe 실행 |
| clawdbot-service | ClawBridge + Gateway 관리 |
| OpenClaw Gateway (node) | AI 에이전트 (:18789) |

**ClawBridge 흐름**:
```
clawdbot-service → TLS TCP 연결 → voicechat.tyranno.xyz:9090
  ← chat_request (앱에서 온 대화 요청)
  → POST http://localhost:18789/v1/chat/completions (OpenClaw)
  ← SSE delta 수신
  → chat_response (delta) → GCP 서버 → 앱
```

## 빌드 & 배포

### 앱 빌드
```powershell
cd E:\Project\My\voice-chat
npm run build
npx cap sync android
cd android
.\gradlew assembleDebug
# APK: android/app/build/outputs/apk/debug/app-debug.apk
```

### S25에 설치
```powershell
adb -s R3CY10AF61Z install -r android/app/build/outputs/apk/debug/app-debug.apk
```

### 서버 배포
```powershell
cd E:\Project\My\voice-chat-server
.\build-linux.bat
.\deploy.bat
```

## 알려진 이슈 & 교훈

- **Samsung S25 AudioHardening**: `setStreamVolume(STREAM_MUSIC, 0)` 차단됨. mute 절대 금지
- **AbortController 타임아웃**: SSE 스트리밍은 오래 걸릴 수 있으므로 60초 이상 필요
- **Instance ID**: 서버 재시작마다 bridge ID가 변경됨 → 앱에 자동 복구 로직 필수
- **Vosk STT**: 품질 저하로 폐기 → Google Cloud STT (REST API)로 교체
- **on-device TTS 선택 이유**: 네트워크 지연 없음, Samsung DND 우회 가능
