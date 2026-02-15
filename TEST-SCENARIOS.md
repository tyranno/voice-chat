# VoiceChat 테스트 시나리오

> 생성일: 2025-02-14  
> 현재 버그: 마이크 인식 표시(waveform)는 보이는데 메시지가 전송되지 않음

---

## 1. 단위 테스트 시나리오

### 1.1 NativeSTT — start/stop/pause/resume

| # | 동작 | 예상 결과 | 검증 포인트 |
|---|------|-----------|-------------|
| S1 | `start()` 최초 호출 | 권한 체크 → available 체크 → 리스너 등록 → `_startRecognition()` | `initialized=true`, `_shouldRestart=true`, `_paused=false` |
| S2 | `start()` 중복 호출 (이미 listening) | 즉시 return, 아무 일도 안 함 | `_isListening || _initializing || _starting` 가드 |
| S3 | `stop()` | `_shouldRestart=false`, 타이머 클리어, `SpeechRecognition.stop()`, `onEnd` 콜백 | `_finalSent=true`로 설정되어 잔여 결과 무시 |
| S4 | `pause()` | `_paused=true`, `_shouldRestart=false`, `SpeechRecognition.stop()` | `onEnd` 호출 안 됨, 자동 재시작 안 됨 |
| S5 | `pause()` 중복 호출 | 즉시 return | `_paused` 가드 |
| S6 | `resume()` | `_paused=false`, `_shouldRestart=true`, 500ms 후 `_startRecognition()` | 500ms 딜레이 존재 확인 |
| S7 | `resume()` 후 즉시 `pause()` | 500ms await 중 `_paused=true` → `_startRecognition` 스킵 | 경쟁 조건 안전성 |

### 1.2 NativeSTT — onInterim/onFinal 콜백 호출 조건

| # | 이벤트 시퀀스 | 예상 콜백 |
|---|---------------|-----------|
| C1 | `partialResults` 수신 (paused=false, finalSent=false) | `onInterim(text)` 호출, `_lastResult` 갱신 |
| C2 | `partialResults` 수신 (paused=true) | 무시됨 — 콜백 없음 |
| C3 | `listeningState:stopped` → (결과 있음) | `_emitFinal()` → `onFinal(text)` 호출 |
| C4 | `listeningState:stopped` → (결과 없음) → 500ms 대기 → partialResults 도착 | `_stoppedTimer` 중 결과 도착 시 `onFinal` 호출 |
| C5 | `listeningState:stopped` → (결과 없음) → 500ms 대기 → 결과 없음 | `onFinal` 호출 없이 재시작만 스케줄 |
| C6 | `partialResults` 도착 + 이미 `_stoppedTimer` 동작 중 | 타이머 클리어 → 즉시 `_emitFinal()` → 재시작 스케줄 |

### 1.3 finalBuffer 축적 → flushFinalBuffer 타이밍 (+page.svelte)

| # | 시나리오 | 예상 동작 |
|---|---------|-----------|
| F1 | `onFinal("안녕")` 1회 호출 | `finalBuffer="안녕"`, `interimText="안녕"`, 1200ms 타이머 시작 |
| F2 | `onFinal("안녕")` → 800ms → `onFinal("하세요")` | `finalBuffer="안녕 하세요"`, 타이머 리셋(다시 1200ms) |
| F3 | `onFinal("안녕")` → 1200ms 경과 | `flushFinalBuffer()` → `sendMessage("안녕")` 호출, `finalBuffer=""` |
| F4 | 마이크 OFF 토글 시 finalBuffer에 텍스트 존재 | 타이머 클리어, `finalBuffer=""`, `interimText=""` — **전송 안 됨** |
| F5 | `onFinal("")` (빈 문자열) | `text.trim()` 체크로 무시됨 |

> **🐛 버그 의심**: `onFinal`이 호출되지 않으면 `finalBuffer`가 영원히 비어있어 메시지 전송 불가. `listeningState:stopped`이 오지 않거나, `_lastResult`가 설정되지 않는 경우 확인 필요.

### 1.4 CapacitorTTS — addChunk → speak → onStart/onEnd

| # | 시나리오 | 예상 콜백 순서 |
|---|---------|----------------|
| T1 | `addChunk("안녕하세요.")` (idle 상태) | `onStart()` → `onSentence("안녕하세요.")` → TTS 재생 → `onEnd()` |
| T2 | `addChunk("첫번째.")` → 재생 중 `addChunk("두번째.")` | `onStart()` → `onSentence("첫번째.")` → `onSentence("두번째.")` → `onEnd()` (onStart 1회만) |
| T3 | `addChunk("문장.")` → 재생 중 `stop()` | `onEnd()` 호출, queue 비워짐, `cancelled=true` |
| T4 | `stop()` 후 `addChunk("새문장.")` | `cancelled=false` 리셋, 새 `onStart()` → 정상 재생 |

### 1.5 에러 케이스

| # | 에러 | 원인 | NativeSTT 동작 |
|---|------|------|----------------|
| E1 | "No match" | 발화 없이 타임아웃 | 에러 아님 — `_lastResult` 있으면 `_emitFinal()`, 없으면 1초 후 재시작 |
| E2 | "not connected" | start() 너무 빨리 호출 (Galaxy A50: 600ms 미만) | 3초 후 재시도 스케줄 |
| E3 | "Missing permission" | 마이크 권한 거부 | `onError('마이크 권한이 필요합니다')`, 재시작 안 함 |
| E4 | Network error (fetch) | 서버 불통 | `fetchWithRetry` 3회 재시도 (1s, 2s, 4s) 후 `onError` |
| E5 | TTS speak error | TTS 엔진 오류 | 다음 문장으로 계속 (루프 안 깨짐) |

---

## 2. E2E 테스트 시나리오

### 시나리오 A: 정상 음성 대화 순환

**플로우**: 마이크 ON → "안녕" 발화 → STT 인식 → 전송 → AI 응답 → TTS 재생 → 마이크 자동 재개

| 단계 | 동작 | 예상 상태 | 확인 사항 |
|------|------|-----------|-----------|
| 1 | 마이크 버튼 탭 | `micEnabled=true`, `state=listening` | waveform 파란색 |
| 2 | "안녕" 발화 | `partialResults` → `onInterim` | `interimText`에 "안녕" 표시 |
| 3 | `listeningState:stopped` | `onFinal("안녕")` → `finalBuffer="안녕"` | — |
| 4 | 1200ms 경과 | `flushFinalBuffer()` → `sendMessage("안녕")` | `state=processing`, 사용자 메시지 버블 표시 |
| 5 | 서버 스트리밍 응답 | `onDelta` → 어시스턴트 메시지 축적 + `tts.addChunk()` | `state=speaking` (TTS onStart에서) |
| 6 | TTS 재생 완료 | `onEnd` → 500ms 후 `stt.resume()` | `state=listening`, STT 재시작 |

**성공 기준**: 전체 순환이 30초 내 완료, 사용자/어시스턴트 메시지 모두 화면에 표시

### 시나리오 B: TTS 재생 중 마이크 피드백 방지

| 단계 | 동작 | 확인 사항 |
|------|------|-----------|
| 1 | AI 응답 수신 → TTS 시작 | `tts.onStart()` → `stt.pause()` 호출됨 |
| 2 | TTS 소리 출력 중 | `stt._paused=true`, `stt._isListening=false` |
| 3 | `partialResults` 이벤트 혹시 발생 | `_paused` 가드로 무시됨 |
| 4 | TTS 완료 | `stt.resume()` → 500ms 후 STT 재시작 |

**성공 기준**: TTS 재생 중 STT가 TTS 소리를 잡아서 엉뚱한 메시지가 전송되지 않음

### 시나리오 C: 연속 발화 (finalBuffer 축적)

| 단계 | 동작 | finalBuffer | interimText |
|------|------|-------------|-------------|
| 1 | "오늘" 발화 → onFinal | `"오늘"` | `"오늘"` |
| 2 | 500ms 후 "날씨" 발화 → onFinal | `"오늘 날씨"` | `"오늘 날씨"` |
| 3 | 400ms 후 "어때" 발화 → onFinal | `"오늘 날씨 어때"` | `"오늘 날씨 어때"` |
| 4 | 1200ms 경과 (침묵) | `""` (flush됨) | `""` |

**성공 기준**: `sendMessage("오늘 날씨 어때")` 1회 호출, 3개 개별 메시지가 아님

### 시나리오 D: 마이크 OFF → ON 토글

| 단계 | 동작 | 예상 |
|------|------|------|
| 1 | 마이크 OFF 상태에서 버튼 탭 | `micEnabled=true`, `stt.start()`, `state=listening` |
| 2 | 마이크 ON 상태에서 버튼 탭 | `micEnabled=false`, `finalTimer` 클리어, `finalBuffer=""`, `stt.stop()`, `tts.stop()`, `state=idle` |
| 3 | 빠르게 ON→OFF→ON (500ms 간격) | 경쟁 조건 없이 최종 ON 상태 유지 |

**성공 기준**: 토글 후 상태가 정확히 반영, 잔여 타이머나 버퍼 없음

### 시나리오 E: 서버 연결 실패

| 단계 | 동작 | 예상 |
|------|------|------|
| 1 | 서버 다운 상태에서 발화 → sendMessage | `fetchWithRetry` 3회 재시도 |
| 2 | 모든 재시도 실패 | `messages[assistantIdx].content = "⚠️ 오류: 연결 실패..."` |
| 3 | 마이크 ON 상태였으면 | STT 재개 (TTS 없으므로 즉시 resume) |

**성공 기준**: 에러 메시지 표시, 앱 크래시 없음, STT 정상 복귀

---

## 3. 체크리스트

### 3.1 Logcat에서 확인해야 할 로그 패턴

| 패턴 | 의미 | 정상/이상 |
|------|------|-----------|
| `[NativeSTT] state: started` | SpeechRecognizer 연결 성공 | ✅ 정상 |
| `[NativeSTT] state: stopped` | 인식 세션 종료 | ✅ 정상 (자동 재시작 따라옴) |
| `[NativeSTT] Result: <text>` | 중간 인식 결과 | ✅ 핵심 — 이게 없으면 STT 결과 자체가 없음 |
| `[NativeSTT] Final: <text>` | 최종 인식 결과 전달 | ✅ **핵심** — 이게 없으면 onFinal 미호출 = 메시지 미전송 |
| `[VoiceChat] STT onEnd` | STT 종료 콜백 | ℹ️ WebSpeech만 |
| `[NativeSTT] start() called, waiting...` | 인식 시작 요청 | ✅ 정상 |
| `[NativeSTT] not connected` | 세션 정리 부족 | ⚠️ 간헐적 OK, 반복되면 이상 |
| `[NativeSTT] Pause` / `Resume` | TTS 연동 pause/resume | ✅ 정상 |
| `[Guardian] STT dead — restarting` | 5초 가디언 재시작 | ⚠️ 가끔 OK, 빈번하면 STT 불안정 |
| `[TTS] speak error` | TTS 재생 실패 | ⚠️ 이상 |

### 3.2 현재 버그 디버깅 — 핵심 확인 순서

**증상**: waveform 보임 (state=listening) + 메시지 전송 안 됨

1. **`[NativeSTT] Result:` 로그 존재?**
   - ❌ 없음 → `partialResults` 이벤트 자체가 안 옴. SpeechRecognizer 문제.
   - ✅ 있음 → 다음 단계

2. **`[NativeSTT] Final:` 로그 존재?**
   - ❌ 없음 → `listeningState:stopped`이 안 오거나, `_emitFinal` 조건 불충족
   - ✅ 있음 → 다음 단계

3. **`flushFinalBuffer` 호출됨?** (`sendMessage` 로그 확인)
   - ❌ 없음 → `finalTimer`가 클리어되거나, `finalBuffer`가 빈 상태
   - ✅ 있음 → 서버 통신 문제

> **가장 유력한 원인**: `listeningState:stopped` 이벤트에서 `_lastResult`가 설정되기 전에 stopped이 와서 "결과 없음" 분기를 타고, 500ms 대기 중에도 partialResults가 안 오는 경우. 또는 `_finalSent`가 이미 `true`인 상태.

### 3.3 각 시나리오 성공/실패 판단 기준

| 시나리오 | 성공 | 실패 |
|---------|------|------|
| A (정상 순환) | 사용자+AI 메시지 모두 표시, TTS 재생 후 STT 재개 | 메시지 미전송, TTS 무음, STT 미재개 |
| B (피드백 방지) | TTS 중 STT 무반응 | TTS 소리가 STT에 잡혀 이상한 메시지 전송 |
| C (연속 발화) | 합쳐진 1개 메시지 전송 | 각각 개별 전송 또는 전송 안 됨 |
| D (토글) | 정확한 state 전환 | state 꼬임, 잔여 타이머 |
| E (서버 실패) | 에러 메시지 표시 + 복귀 | 크래시, 무한 로딩 |

### 3.4 ADB Logcat 명령어

```bash
# 전체 VoiceChat 로그 (NativeSTT + UI)
adb logcat -s Capacitor:V CapacitorHttp:V | grep -E "\[NativeSTT\]|\[VoiceChat\]|\[TTS\]"

# NativeSTT만 집중
adb logcat | grep "\[NativeSTT\]"

# 시나리오 A: 전체 파이프라인 추적
adb logcat | grep -E "NativeSTT|VoiceChat|TTS|streamChat"

# 현재 버그 디버깅: Result/Final 존재 여부 확인
adb logcat | grep -E "\[NativeSTT\] (Result|Final|state)"

# SpeechRecognizer 네이티브 에러 포함
adb logcat -s Capacitor:V | grep -iE "speech|recogni|NativeSTT"

# 타임스탬프 포함 (타이밍 분석)
adb logcat -v time | grep -E "\[NativeSTT\]|\[VoiceChat\]"

# 로그 클리어 후 깨끗하게 시작
adb logcat -c && adb logcat | grep -E "\[NativeSTT\]|\[VoiceChat\]|\[TTS\]"
```

---

## 4. 즉시 확인 권장 사항 (현재 버그 관련)

1. **`adb logcat | grep "\[NativeSTT\] Result"` 실행** — 음성 인식 결과가 아예 안 오는지 확인
2. **`adb logcat | grep "\[NativeSTT\] state"` 실행** — `started` → `stopped` 순환이 정상인지 확인
3. **`partialResults` 리스너의 `event.matches` 구조 로깅 추가** — `@capgo` 플러그인 버전에 따라 구조가 다를 수 있음
4. **`_finalSent` 플래그 상태 추적** — `listeningState:started`에서 리셋되는데, started가 안 오면 계속 `true`로 남아 결과 무시
