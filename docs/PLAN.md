# 🎙️ VoiceChat — OpenClaw 음성 챗 앱

## 개요

OpenClaw Gateway와 연동하는 **음성 전용 AI 챗 앱**.
마이크로 말하면 AI(렉스)가 음성으로 대답하는 자연스러운 대화 앱.
갤럭시 제미나이처럼 버튼/재생 없이 자동으로 듣고 말하는 UX.

## 기술 스택

| 레이어 | 기술 | 버전/비고 |
|--------|------|----------|
| 프레임워크 | **SvelteKit 5** (Svelte 5 runes) | 최신 |
| 하이브리드 | **Capacitor 6** | Android APK 빌드 |
| UI | **Tailwind CSS 4** | |
| AI 백엔드 | **OpenClaw Gateway** | OpenAI 호환 HTTP API |
| STT | **Deepgram** (실시간 WebSocket) | 1차 / Web Speech API (폴백) |
| TTS | **ElevenLabs Streaming** | 1차 / Google TTS (폴백) |
| VAD | **@ricky0123/vad-web** (Silero VAD) | 브라우저 내 음성 감지 |
| 상태관리 | Svelte 5 runes ($state, $derived) | |

## 인프라

| 구분 | 환경 | 비고 |
|------|------|------|
| **앱** | Android (Capacitor APK) | 사용자 디바이스 |
| **중계 서버** | **Google Cloud (GCP)** | STT/TTS 프록시 + 정적 호스팅 |
| **AI 백엔드** | OpenClaw Gateway (마스터 PC) | 기존 환경 그대로 |

### GCP 서버 역할
- STT WebSocket 프록시 (Deepgram API 키 보호)
- TTS 프록시 (ElevenLabs API 키 보호)
- OpenClaw Gateway 중계 (외부 노출 없이 터널링)
- 웹 버전 호스팅 (선택)

### GCP 추천 구성
| 서비스 | 용도 | 예상 비용 |
|--------|------|----------|
| **Cloud Run** | 중계 서버 (Node.js) | 무료 티어 충분 (월 200만 요청) |
| **Cloud Run** 또는 **Compute Engine f1-micro** | 상시 WebSocket 프록시 | 무료 티어 / ~$5/월 |
| **Tailscale** | GCP ↔ 마스터PC 터널 | 무료 (개인) |

## 아키텍처

```
┌──────────────────────────────────────┐
│          Android App (Capacitor)      │
│  ┌──────────────────────────────┐    │
│  │     SvelteKit 5 (WebView)     │    │
│  │                               │    │
│  │  [VAD] → 음성 감지 시작/끝    │    │
│  │  [STT] → 실시간 텍스트 변환   │    │
│  │  [TTS] → 응답 음성 자동재생   │    │
│  └──────────┬───────────────────┘    │
│             │ HTTPS / WSS            │
└─────────────┼────────────────────────┘
              │
              ▼
┌──────────────────────────────────────┐
│       GCP 중계 서버 (Cloud Run)       │
│                                       │
│  /api/chat  → OpenClaw 프록시 (SSE)  │
│  /api/stt   → Deepgram WebSocket     │
│  /api/tts   → ElevenLabs 스트리밍    │
│                                       │
│  (API 키 보호 + CORS + 인증)         │
└──────────────┬───────────────────────┘
               │ Tailscale 터널
               ▼
┌──────────────────────────────────────┐
│   마스터 PC — OpenClaw Gateway        │
│   POST /v1/chat/completions          │
│   - stream: true (SSE)               │
│   - x-openclaw-agent-id: main        │
│   - user: "voicechat-app" (세션유지) │
│                                       │
│   렉스(Rex) 🦖                        │
│   - 메모리, 도구, 스킬 전부 사용     │
│   - 텔레그램과 동일한 AI              │
└──────────────────────────────────────┘
```

## 데이터 플로우

```
1. [사용자 말함]
2. VAD가 음성 시작 감지 → 마이크 활성화
3. 음성 데이터 → Deepgram WebSocket (실시간 STT)
4. 실시간 자막 표시 (말하는 중)
5. VAD가 음성 끝 감지 → 최종 텍스트 확정
6. 텍스트 → OpenClaw Gateway (POST /v1/chat/completions, stream:true)
7. SSE 스트리밍 수신 → 문장 단위 분리
8. 문장 → ElevenLabs TTS → 음성 버퍼 → 자동 재생
9. 화면에 AI 응답 텍스트 표시 (동시)
10. 재생 끝 → 다시 듣기 모드 (VAD 활성)
    * 재생 중 사용자가 말하면 → 즉시 중단 (barge-in)
```

## 화면 구성

### 메인 (대화 화면)
```
┌─────────────────────────┐
│  🦖 렉스          ⚙️    │  ← 헤더 (설정 버튼)
│                         │
│  ┌───────────────────┐  │
│  │                   │  │
│  │   나: "오늘 주식  │  │  ← 대화 내역 (스크롤)
│  │        어때?"     │  │
│  │                   │  │
│  │   🦖: "오늘 코스피│  │
│  │   는 2,650으로..." │  │
│  │                   │  │
│  └───────────────────┘  │
│                         │
│      ╭─────────╮        │
│      │ ∿∿∿∿∿∿  │        │  ← 파형 시각화
│      ╰─────────╯        │     (듣는 중: 파란색)
│                         │     (AI 말하는 중: 초록색)
│   "오늘 주식 어때?"     │  ← 실시간 자막
│                         │
│      🎤 듣는 중...      │  ← 상태 표시
└─────────────────────────┘
```

### 설정 화면
```
┌─────────────────────────┐
│  ← 설정                 │
│                         │
│  🔊 음성 설정            │
│  ├ TTS 엔진: ElevenLabs │
│  ├ 음성: Rachel (여성)   │
│  └ 속도: 1.0x           │
│                         │
│  🎤 입력 설정            │
│  ├ STT 엔진: Deepgram   │
│  ├ 언어: 한국어          │
│  └ VAD 감도: 보통        │
│                         │
│  🔗 서버 설정            │
│  ├ Gateway: 192.168.x.x │
│  ├ Port: 18789          │
│  └ Token: ****          │
│                         │
│  💬 텍스트 입력 모드      │
│  └ [토글] 키보드 입력    │
└─────────────────────────┘
```

## OpenClaw Gateway 연동

### 설정 활성화 필요
```json5
{
  gateway: {
    http: {
      endpoints: {
        chatCompletions: { enabled: true }
      }
    }
  }
}
```

### API 호출 예시
```javascript
// SSE 스트리밍 요청
const response = await fetch('http://<gateway>:18789/v1/chat/completions', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer <token>',
    'Content-Type': 'application/json',
    'x-openclaw-agent-id': 'main'
  },
  body: JSON.stringify({
    model: 'openclaw',
    stream: true,
    user: 'voicechat-app',  // 세션 유지용
    messages: [
      { role: 'user', content: '오늘 주식 어때?' }
    ]
  })
});

// SSE 파싱
const reader = response.body.getReader();
// ... 문장 단위로 TTS 전송
```

## 프로젝트 구조

```
voice-chat/
├── docs/
│   └── PLAN.md              ← 이 문서
├── src/
│   ├── lib/
│   │   ├── audio/
│   │   │   ├── vad.ts       ← VAD (음성 감지)
│   │   │   ├── recorder.ts  ← 마이크 녹음
│   │   │   ├── player.ts    ← 오디오 재생 큐
│   │   │   └── visualizer.ts ← 파형 시각화
│   │   ├── stt/
│   │   │   ├── deepgram.ts  ← Deepgram WebSocket STT
│   │   │   └── webspeech.ts ← Web Speech API (폴백)
│   │   ├── tts/
│   │   │   ├── elevenlabs.ts ← ElevenLabs 스트리밍 TTS
│   │   │   └── google.ts    ← Google TTS (폴백)
│   │   ├── api/
│   │   │   └── openclaw.ts  ← OpenClaw Gateway 클라이언트
│   │   ├── stores/
│   │   │   ├── chat.svelte.ts    ← 대화 상태
│   │   │   ├── audio.svelte.ts   ← 오디오 상태
│   │   │   └── settings.svelte.ts ← 설정
│   │   └── utils/
│   │       └── sentence.ts  ← 문장 분리 유틸
│   ├── routes/
│   │   ├── +layout.svelte
│   │   ├── +page.svelte     ← 메인 대화 화면
│   │   └── settings/
│   │       └── +page.svelte ← 설정 화면
│   └── app.html
├── static/
│   └── models/
│       └── silero_vad.onnx  ← VAD 모델 파일
├── capacitor.config.ts
├── svelte.config.js
├── tailwind.config.js
├── package.json
└── README.md
```

## 개발 단계

### Phase 1: 기본 셋업 (2일)
- [ ] SvelteKit 5 + Capacitor 6 + Tailwind 4 프로젝트 초기화
- [ ] Android 빌드 환경 구성
- [ ] 기본 라우팅 (메인 / 설정)

### Phase 2: OpenClaw 연동 (2일)
- [ ] Gateway chatCompletions 엔드포인트 활성화
- [ ] SSE 스트리밍 클라이언트 구현
- [ ] 텍스트 채팅 기본 동작 확인
- [ ] 세션 유지 (user 파라미터)

### Phase 3: 음성 입력 — STT (3일)
- [ ] 마이크 권한 + Capacitor 플러그인
- [ ] VAD 연동 (자동 감지)
- [ ] Deepgram WebSocket 실시간 STT
- [ ] 실시간 자막 표시
- [ ] Web Speech API 폴백

### Phase 4: 음성 출력 — TTS (3일)
- [ ] ElevenLabs 스트리밍 TTS 연동
- [ ] 문장 단위 분리 + 순차 재생
- [ ] 오디오 큐 관리 (끊김 없는 재생)
- [ ] Google TTS 폴백

### Phase 5: 대화 UX (2일)
- [ ] Barge-in (AI 말하는 중 끊기)
- [ ] 파형 애니메이션 (듣기/말하기 상태)
- [ ] 상태 전환 (idle → listening → processing → speaking)
- [ ] 대화 기록 로컬 저장

### Phase 6: 설정 + 마무리 (2일)
- [ ] 설정 화면 (TTS 음성/STT 엔진/서버)
- [ ] 텍스트 입력 모드 토글
- [ ] 에러 핸들링 + 네트워크 재연결
- [ ] APK 빌드 + 실기기 테스트

### Phase 7: 고도화 (선택)
- [ ] 웨이크워드 ("렉스야") — Porcupine / Picovoice
- [ ] 오프라인 STT (Whisper.cpp WASM)
- [ ] 위젯 / 알림바에서 바로 음성 입력
- [ ] Wear OS 연동

## 예상 비용 (월)

| 서비스 | 무료 티어 | 유료 |
|--------|----------|------|
| GCP Cloud Run | 월 200만 요청 무료 | $0~ |
| Deepgram STT | 월 $200 크레딧 (신규) | $0.0043/분 |
| ElevenLabs TTS | 1만자/월 무료 | $5/월 (3만자) |
| OpenClaw | 기존 구독 사용 | 추가비용 없음 |
| Tailscale | 개인 무료 | $0 |
| **합계** | **$0 (무료 티어)** | **~$5-15/월** |

## 핵심 장점

1. **AI 백엔드 개발 불필요** — OpenClaw(렉스)가 그대로 동작
2. **동일한 AI** — 텔레그램에서 대화하던 렉스와 완전 동일
3. **도구/스킬 사용** — 주식 조회, 일정, 웹 검색 등 전부 가능
4. **메모리 공유** — 텔레그램 대화 맥락 그대로 이어감
5. **비용 효율** — 별도 AI API 비용 없음
6. **SvelteKit 5** — 마스터 기존 기술 스택 활용

## 선결 조건

- [ ] OpenClaw Gateway `chatCompletions` 엔드포인트 활성화
- [ ] GCP 프로젝트 생성 + Cloud Run 설정
- [ ] Tailscale 설치 (마스터 PC + GCP 서버)
- [ ] Deepgram API 키 발급
- [ ] ElevenLabs API 키 발급 (또는 Google TTS로 시작)
- [ ] Android Studio + JDK 설치 (APK 빌드용)

## GCP 중계 서버 구조

```
voice-chat-server/
├── src/
│   ├── index.ts          ← Express/Hono 서버
│   ├── routes/
│   │   ├── chat.ts       ← OpenClaw 프록시 (SSE 중계)
│   │   ├── stt.ts        ← Deepgram WebSocket 프록시
│   │   └── tts.ts        ← ElevenLabs 프록시
│   ├── middleware/
│   │   └── auth.ts       ← 앱 인증 (JWT/토큰)
│   └── config.ts         ← 환경변수 관리
├── Dockerfile
├── cloudbuild.yaml
└── package.json
```

### 배포 명령
```bash
gcloud run deploy voice-chat-server \
  --source . \
  --region asia-northeast3 \
  --allow-unauthenticated \
  --set-env-vars "OPENCLAW_URL=http://100.x.x.x:18789,DEEPGRAM_KEY=xxx,ELEVENLABS_KEY=xxx"
```

### 왜 GCP 중계가 필요한가
1. **API 키 보호** — STT/TTS API 키가 앱에 노출되지 않음
2. **OpenClaw 비노출** — 마스터 PC가 인터넷에 직접 노출 안 됨
3. **Tailscale 터널** — GCP ↔ 마스터PC 사설 네트워크
4. **HTTPS** — Cloud Run이 자동으로 SSL 인증서 제공
5. **스케일링** — 필요 시 자동 확장
