# VoiceChat 아키텍처 설계안

> 작성일: 2025-02-14 | 상태: 코딩 에이전트 실행 전 설계안

## 1. 현재 문제 요약

**증상:** 마이크 인식 UI는 활성화되나 메시지가 전송되지 않음

### 근본 원인: 두 개의 STT 시스템 충돌

현재 Android에서 STT가 **이중 등록**되어 있음:

| 파일 | 사용하는 것 | 역할 |
|------|------------|------|
| `native.ts` | `@capgo/capacitor-speech-recognition` (SpeechRecognition) | @capgo 플러그인의 `partialResults`, `listeningState` 이벤트 수신 |
| `NativeSttPlugin.java` | Android `SpeechRecognizer` 직접 사용 | 자체 `sttResult` 이벤트 발신 |

**충돌 메커니즘:**
1. `native.ts`는 `@capgo/capacitor-speech-recognition`의 `SpeechRecognition.start()`를 호출
2. `NativeSttPlugin.java`는 `MainActivity`에 등록되어 있고, 자체 `SpeechRecognizer`를 생성
3. **두 플러그인 모두 Android `SpeechRecognizer`를 사용** → 하나의 기기에서 동시에 두 recognizer가 충돌
4. `native.ts`는 `NativeSttPlugin`의 `muteSystemSounds`/`unmuteSystemSounds`만 사용하지만, **NativeSttPlugin의 start/stop/pause/resume 메서드도 존재**하여 혼란 유발

**추가 문제:**
- `capacitor.ts` — @capgo의 `continuous: true` 모드를 사용하는 또 다른 wrapper. 현재 import는 되지만 Android에서는 `NativeSTT`가 선택됨
- `vosk.ts` — 제거 예정이지만 파일이 남아있음
- `settings.sttEngine` — `'webspeech' | 'deepgram'` 타입인데 실제로는 사용되지 않음 (하드코딩된 platform 체크로 STT 선택)

## 2. 현재 데이터 흐름 (의도된 것)

```
[마이크 ON] → toggleMic()
  → conversation.setListening()
  → NativeSTT.start()
    → @capgo SpeechRecognition.start({ partialResults: true })
    → partialResults 이벤트 → onInterim(text)
    → listeningState:'stopped' → _emitFinal(text) → onFinal(text)

onFinal(text):
  → finalBuffer += text
  → 1200ms 디바운스 타이머 시작
  → 타이머 만료 → flushFinalBuffer()
    → sendMessage(text)
      → conversation.setProcessing()
      → streamChat() → 서버 API 호출
      → 응답 delta → TTS.addChunk()
        → TTS.onStart → conversation.setSpeaking() + STT.pause()
        → TTS.onEnd → conversation.setListening() + STT.resume()
```

**문제 지점:**
- `_emitFinal()`이 호출되려면 `partialResults`에서 `_lastResult`가 설정되어야 함
- @capgo 플러그인과 NativeSttPlugin.java가 동시에 Android SpeechRecognizer를 점유하면 이벤트가 안 올 수 있음

## 3. 올바른 아키텍처 설계

### 3.1 STT 엔진 단일화

**결정: `NativeSttPlugin.java`를 STT의 단일 진실 공급원(single source of truth)으로 사용**

이유:
- 이미 완성도 높은 Java 구현이 있음 (자동 재시작, 중복 제거, Google 인식 우선)
- @capgo 플러그인의 내부 동작을 제어할 수 없음 (continuous 모드 불안정)
- 비프음 제거(mute/unmute)가 같은 플러그인에 있어 타이밍 제어 용이

**제거할 것:**
- `src/lib/stt/capacitor.ts` — 삭제
- `src/lib/stt/vosk.ts` — 삭제
- `@capgo/capacitor-speech-recognition` — **STT 용도로는 제거** (native.ts에서 import 제거)
- `src/lib/stt/native.ts` — **NativeSttPlugin.java의 이벤트를 수신하도록 전면 재작성**

**유지할 것:**
- `src/lib/stt/webspeech.ts` — 웹 브라우저용 (변경 없음)
- `NativeSttPlugin.java` — Android 네이티브 STT (기존 유지, 약간의 개선)

### 3.2 새로운 `native.ts` 설계

```typescript
// NativeSttPlugin.java의 Capacitor 이벤트를 직접 수신
import { registerPlugin } from '@capacitor/core';
import type { PluginListenerHandle } from '@capacitor/core';

interface NativeSttPlugin {
  start(): Promise<void>;
  stop(): Promise<void>;
  pause(): Promise<void>;
  resume(): Promise<void>;
  isListening(): Promise<{ listening: boolean }>;
  muteSystemSounds(): Promise<void>;
  unmuteSystemSounds(): Promise<void>;
  addListener(event: 'sttResult', handler: (data: { type: 'partial' | 'final'; text: string }) => void): Promise<PluginListenerHandle>;
}

const NativeStt = registerPlugin<NativeSttPlugin>('NativeStt');
```

**핵심 변경:**
- `@capgo/capacitor-speech-recognition` 완전 제거
- `NativeStt` 플러그인 하나로 start/stop/pause/resume/mute 모두 처리
- Java쪽 `notifyListeners("sttResult", ...)` → JS쪽 `addListener("sttResult", ...)` 직결
- JS에서의 복잡한 타이머/재시작 로직 제거 (Java가 자체 관리)

### 3.3 전체 파이프라인

```
┌─────────────────────────────────────────────────┐
│                  +page.svelte                    │
│                                                  │
│  toggleMic() → NativeSTT.start()                │
│                    │                             │
│  ┌─────────────────▼──────────────────┐         │
│  │         NativeSttPlugin.java        │         │
│  │  - SpeechRecognizer 생성/관리       │         │
│  │  - 자동 재시작 (1500ms)            │         │
│  │  - mute/unmute 시스템 사운드       │         │
│  │  - 중복 결과 필터링                │         │
│  │  - sttResult 이벤트 발신           │         │
│  └──────────┬──────────┬──────────────┘         │
│       partial│    final│                         │
│  ┌──────────▼──────────▼──────────────┐         │
│  │       native.ts (thin wrapper)      │         │
│  │  - addListener('sttResult')         │         │
│  │  - partial → onInterim callback     │         │
│  │  - final → onFinal callback         │         │
│  └──────────┬──────────┬──────────────┘         │
│       interim│    final│                         │
│  ┌──────────▼──────────▼──────────────┐         │
│  │         +page.svelte 콜백           │         │
│  │  onInterim → interimText 표시       │         │
│  │  onFinal → finalBuffer 축적         │         │
│  │  1200ms 무입력 → flushFinalBuffer() │         │
│  └─────────────────┬──────────────────┘         │
│                    │                             │
│  ┌─────────────────▼──────────────────┐         │
│  │          sendMessage(text)          │         │
│  │  → conversation.setProcessing()     │         │
│  │  → streamChat() API 호출            │         │
│  └─────────────────┬──────────────────┘         │
│                    │                             │
│  ┌─────────────────▼──────────────────┐         │
│  │        CapacitorTTS.addChunk()      │         │
│  │  onStart → STT.pause() + setSpeaking│         │
│  │  onEnd → STT.resume() + setListening│         │
│  └────────────────────────────────────┘         │
└─────────────────────────────────────────────────┘
```

### 3.4 TTS↔STT 피드백 루프 방지

현재 설계는 이미 올바름. 유지할 것:

```
TTS.onStart:
  1. conversation.setSpeaking()
  2. NativeStt.pause() → Java: shouldRestart=false, recognizer.destroy()
  3. muteSystemSounds()는 불필요 (recognizer가 꺼져있으므로)

TTS.onEnd:
  1. 500ms 대기 (TTS 잔향 방지)
  2. conversation.setListening()
  3. NativeStt.resume() → Java: shouldRestart=true, startListening()
```

**개선점:**
- `native.ts`에서 pause/resume을 NativeStt 플러그인으로 직접 전달 (현재는 @capgo stop + 복잡한 JS 로직)
- mute/unmute는 Java의 `startListening()` / `stopRecognizer()` 안에서 자동 처리

### 3.5 에러 핸들링

Java `NativeSttPlugin`이 이미 처리하는 것:
- `ERROR_NO_MATCH` → 자동 재시작 (1500ms)
- `ERROR_SPEECH_TIMEOUT` → 자동 재시작
- `ERROR_CLIENT` → 자동 재시작

JS에서 추가할 것:
- `sttResult` 이벤트에 `type: 'error'`도 추가하여 UI에 표시 가능하게
- 연속 5회 이상 에러 시 사용자에게 알림

### 3.6 Settings 정리

`settings.svelte.ts`의 `sttEngine` 타입 변경:
```typescript
sttEngine: 'native' | 'webspeech';  // 'deepgram' 제거
```
- Android → 자동으로 `'native'` (NativeSttPlugin)
- 웹 → `'webspeech'` (WebSpeechSTT)
- `sttEngine` 설정은 실제로 사용하거나, 아니면 완전히 제거하고 platform 체크만 사용

## 4. 코딩 에이전트 실행 체크리스트

### Phase 1: 정리
- [ ] `src/lib/stt/vosk.ts` 삭제
- [ ] `src/lib/stt/capacitor.ts` 삭제
- [ ] `package.json`에서 `@capgo/capacitor-speech-recognition` 의존성 제거 (또는 유지 판단)
- [ ] `+page.svelte`에서 `CapacitorSTT` import 제거

### Phase 2: native.ts 재작성
- [ ] `native.ts`를 `NativeSttPlugin.java`의 thin wrapper로 재작성
- [ ] `registerPlugin('NativeStt')`로 start/stop/pause/resume/addListener 사용
- [ ] @capgo import 완전 제거
- [ ] JS측 복잡한 타이머/재시작 로직 제거 (Java가 관리)

### Phase 3: Java 플러그인 개선
- [ ] `NativeSttPlugin.java`에 에러 이벤트 추가: `notifyListeners("sttResult", { type: "error", text: errorMsg })`
- [ ] mute/unmute를 startListening/stopRecognizer 내부로 이동 (선택적)

### Phase 4: 통합 테스트
- [ ] 마이크 ON → 음성 인식 → finalBuffer 축적 → 메시지 전송 확인
- [ ] TTS 재생 중 STT 일시정지 → TTS 끝 → STT 재개 확인
- [ ] 침묵 시 자동 재시작 확인
- [ ] 에러 후 복구 확인

## 5. 파일별 변경 요약

| 파일 | 액션 |
|------|------|
| `stt/vosk.ts` | **삭제** |
| `stt/capacitor.ts` | **삭제** |
| `stt/native.ts` | **전면 재작성** — NativeStt 플러그인 직접 사용 |
| `stt/webspeech.ts` | 변경 없음 |
| `+page.svelte` | CapacitorSTT import 제거, NativeSTT 사용법 업데이트 |
| `NativeSttPlugin.java` | 에러 이벤트 추가 (선택적) |
| `MainActivity.java` | 변경 없음 |
| `conversation.svelte.ts` | 변경 없음 |
| `settings.svelte.ts` | sttEngine 타입 정리 (선택적) |
| `api/openclaw.ts` | 변경 없음 |
| `tts/capacitor.ts` | 변경 없음 |
