# VoiceChat 앱 코드 분석 및 리팩토링 계획

## 📊 현재 상황 요약

- **프로젝트**: SvelteKit + Capacitor 기반 Android 음성 채팅 앱
- **핵심 기능**: 마이크 ON → STT → AI 응답 → TTS → 마이크 자동 재시작 (무한 루프)
- **기술 스택**: @capgo/capacitor-speech-recognition (STT), @capacitor-community/text-to-speech (TTS)
- **타겟 디바이스**: Samsung Galaxy A50 (Android 11)

## 🐛 발견된 주요 버그/문제점

### 1. STT 중복 전송 문제 (Critical)
**문제**: 한 번 말하면 2번 인식되어 AI에게 같은 메시지가 두 번 전송됨

**원인 분석**:
- `NativeSTT.ts`에서 `partialResults` 이벤트와 `listeningState.stopped` 이벤트 모두에서 텍스트 처리
- `_resultSent` 플래그로 중복 방지 시도하지만, 타이밍 이슈로 실패
- `partialResults`에서 `onInterim` 호출하고 동시에 `_lastResult` 업데이트
- `listeningState.stopped`에서 다시 `_lastResult`를 `onFinal`로 전송

**구체적 플로우**:
```
1. 사용자가 "안녕하세요" 발화
2. partialResults 이벤트: "안녕하세요" → onInterim 호출 → _lastResult = "안녕하세요"
3. listeningState: stopped → _lastResult가 있고 _resultSent=false → onFinal 호출
4. +page.svelte에서 onFinal → finalBuffer에 추가 → debounce 후 sendMessage
5. 그런데 어떤 경우에는 partialResults가 여러 번 호출되거나 다른 경로로 중복 전송
```

### 2. 권한 처리 및 Guardian 충돌 (Critical)
**문제**: 권한 요청 중에 micGuardian이 STT 재시작을 시도해서 "Missing permission" 에러 발생

**원인**:
- `+page.svelte`의 `micGuardian` (2초마다 실행)이 STT 상태를 체크하고 죽어있으면 재시작
- 권한 요청 팝업이 뜬 상태에서도 Guardian이 동작
- 권한이 없는 상태에서 `stt.start()` 호출 → "Missing permission" 에러
- Guardian이 에러 상황을 제대로 감지하지 못하고 계속 재시도

### 3. 이벤트 리스너 중복 등록 (Memory Leak)
**문제**: 앱 재시작 시 이벤트 리스너가 중복으로 등록될 가능성

**원인**:
```typescript
// NativeSTT.ts - addListener가 누적됨
await SpeechRecognition.addListener('partialResults', ...);
await SpeechRecognition.addListener('listeningState', ...);
```
- `removeAllListeners()`가 없음
- 앱이 여러 번 초기화될 때 리스너가 쌓임

### 4. 타이머/리소스 정리 부족
**문제**: 
- `finalTimer` 정리 불완전
- `micGuardian` interval이 의존성 배열 밖에서 생성되어 정리되지 않을 수 있음
- `animFrame` 정리는 있지만 다른 비동기 작업들의 정리 로직 부족

### 5. 상태 관리 분산 및 불일치
**문제**:
- `conversation.state` (store)와 `stt.isListening` (클래스)의 상태가 서로 다를 수 있음
- `micEnabled` 플래그와 실제 STT 동작 상태가 불일치
- 에러 발생 시 상태 복구 로직 부족

### 6. 에러 처리 및 복구 메커니즘 부족
**문제**:
- STT 에러 시 단순히 에러 메시지만 표시, 자동 복구 로직 부족
- TTS 에러 시 상태가 `speaking`에서 멈출 수 있음
- 네트워크 에러나 권한 에러 등 각 에러 유형별 대응 전략 부족

### 7. Guardian 로직의 과도한 간섭
**문제**:
- 2초마다 강제로 STT 재시작 시도
- 정상적인 흐름을 방해할 수 있음 (예: TTS 재생 중, 권한 요청 중)
- 상태 체크 조건이 불완전

## 🏗️ 구조적 문제점

### 1. 책임 분산과 결합도
**문제**: 
- STT/TTS 생명주기 관리가 `+page.svelte`에 과도하게 집중
- Guardian 로직이 UI 컴포넌트 안에 있어 테스트/유지보수 어려움

### 2. 상태 머신 불완전
**문제**:
- `conversation` store의 상태 머신이 실제 STT/TTS 상태와 동기화되지 않음
- transition 조건과 예외 상황 처리가 명확하지 않음

### 3. 에러 바운더리 부족
**문제**:
- 각 컴포넌트별 에러 처리가 분산
- 전역 에러 처리 메커니즘 없음

## 📋 리팩토링 계획

### Phase 1: 버그 수정 (Critical Issues)

#### 1.1. STT 중복 전송 문제 해결
**파일**: `src/lib/stt/native.ts`

**변경 사항**:
```typescript
// 현재 문제가 있는 방식
await SpeechRecognition.addListener('partialResults', (event) => {
    // interim으로만 처리, final은 stopped에서
    this.callbacks.onInterim(text);
});

await SpeechRecognition.addListener('listeningState', (event) => {
    if (event.status === 'stopped') {
        // 여기서 final 처리 → 중복 전송
        this.callbacks.onFinal(this._lastResult);
    }
});

// ✅ 개선안
await SpeechRecognition.addListener('partialResults', (event) => {
    if (event.matches && event.matches.length > 0) {
        const text = event.matches[0];
        // interim만 처리, final 플래그 업데이트는 별도
        this.callbacks.onInterim(text);
        this._currentText = text;
    }
});

// 'finalResults' 이벤트 별도 처리 (있다면)
await SpeechRecognition.addListener('finalResults', (event) => {
    // 최종 결과는 여기서만 처리
    if (event.matches && event.matches.length > 0) {
        const finalText = event.matches[0];
        this.callbacks.onFinal(finalText);
    }
});

await SpeechRecognition.addListener('listeningState', (event) => {
    if (event.status === 'stopped') {
        this._isListening = false;
        // ✅ final 전송은 finalResults 이벤트에서만
        // 자동 재시작 로직만 여기서
        if (this._shouldRestart) {
            setTimeout(() => this._startRecognition(), 1000);
        }
    }
});
```

#### 1.2. 권한 처리 개선
**파일**: `src/lib/stt/native.ts`, `src/routes/+page.svelte`

**변경 사항**:
1. **권한 상태 추가 관리**:
```typescript
// NativeSTT에 권한 상태 추가
private _permissionState: 'unknown' | 'requesting' | 'granted' | 'denied' = 'unknown';

private async _checkAndRequestPermission(): Promise<boolean> {
    if (this._permissionState === 'requesting') {
        throw new Error('Permission already being requested');
    }
    
    this._permissionState = 'requesting';
    try {
        const perm = await SpeechRecognition.checkPermissions();
        if (perm.speechRecognition !== 'granted') {
            const result = await SpeechRecognition.requestPermissions();
            this._permissionState = result.speechRecognition === 'granted' ? 'granted' : 'denied';
        } else {
            this._permissionState = 'granted';
        }
        return this._permissionState === 'granted';
    } finally {
        if (this._permissionState === 'requesting') {
            this._permissionState = 'unknown';
        }
    }
}
```

2. **Guardian 로직 개선**:
```typescript
// +page.svelte의 micGuardian 개선
const micGuardian = setInterval(() => {
    // ✅ 권한 요청 중이면 Guardian 중지
    if (!conversation.micEnabled || isLoading || 
        (stt instanceof NativeSTT && stt.isRequestingPermission)) {
        return;
    }
    
    if (conversation.state === 'listening' && stt && !stt.isListening) {
        addDebug('[Guardian] STT dead — restarting');
        stt.start().catch(err => {
            addDebug(`[Guardian] Restart failed: ${err}`);
        });
    }
}, 2000);
```

#### 1.3. 이벤트 리스너 정리
**파일**: `src/lib/stt/native.ts`

**변경 사항**:
```typescript
export class NativeSTT {
    private listenerIds: string[] = []; // 리스너 ID 추적
    
    private async _setupListeners() {
        // 기존 리스너 정리
        await this._cleanupListeners();
        
        const partialId = await SpeechRecognition.addListener('partialResults', ...);
        const stateId = await SpeechRecognition.addListener('listeningState', ...);
        
        this.listenerIds.push(partialId, stateId);
    }
    
    private async _cleanupListeners() {
        for (const id of this.listenerIds) {
            try {
                await SpeechRecognition.removeListener(id);
            } catch (e) {
                console.warn('Failed to remove listener:', id, e);
            }
        }
        this.listenerIds = [];
    }
    
    async destroy() {
        await this._cleanupListeners();
        this._shouldRestart = false;
        this._isListening = false;
    }
}
```

### Phase 2: 구조 개선

#### 2.1. VoiceController 클래스 생성
**새 파일**: `src/lib/voice/VoiceController.ts`

**목적**: STT/TTS 통합 관리, 상태 동기화, Guardian 로직 분리

```typescript
export class VoiceController {
    private stt: NativeSTT | null = null;
    private tts: CapacitorTTS | null = null;
    private guardianInterval: ReturnType<typeof setInterval> | null = null;
    private _state: VoiceState = 'idle';
    
    // 통합 상태 관리
    get state() { return this._state; }
    get isListening() { return this.stt?.isListening ?? false; }
    get isSpeaking() { return this.tts?.isSpeaking ?? false; }
    
    // Guardian 로직을 클래스 내부로
    private startGuardian() {
        this.guardianInterval = setInterval(() => {
            this._guardianCheck();
        }, 2000);
    }
    
    private _guardianCheck() {
        // 개선된 Guardian 로직
    }
    
    async destroy() {
        if (this.guardianInterval) {
            clearInterval(this.guardianInterval);
        }
        await this.stt?.destroy();
        await this.tts?.stop();
    }
}
```

#### 2.2. 상태 머신 개선
**파일**: `src/lib/stores/conversation.svelte.ts`

**변경 사항**:
```typescript
// 상태 전이 규칙 명확화
class ConversationStore {
    // 유효한 전이만 허용하는 메서드들
    private canTransitionTo(newState: ConversationState): boolean {
        const transitions = {
            'idle': ['listening'],
            'listening': ['processing', 'idle'],
            'processing': ['speaking', 'idle'],
            'speaking': ['listening', 'idle']
        };
        return transitions[this.state].includes(newState);
    }
    
    private setState(newState: ConversationState) {
        if (this.canTransitionTo(newState)) {
            this.state = newState;
        } else {
            console.warn(`Invalid transition: ${this.state} → ${newState}`);
        }
    }
}
```

### Phase 3: 에러 처리 및 복구 메커니즘

#### 3.1. ErrorHandler 클래스
**새 파일**: `src/lib/errors/ErrorHandler.ts`

```typescript
export class VoiceErrorHandler {
    static handleSTTError(error: Error, stt: NativeSTT, conversation: ConversationStore) {
        if (error.message.includes('Missing permission')) {
            // 권한 재요청
            return this.handlePermissionError();
        } else if (error.message.includes('network')) {
            // 네트워크 에러 - 재시도
            return this.scheduleRetry(() => stt.start(), 3000);
        }
        // 기타 에러 처리...
    }
    
    private static async handlePermissionError() {
        // 권한 재요청 및 사용자 안내
    }
    
    private static scheduleRetry(fn: Function, delay: number) {
        setTimeout(fn, delay);
    }
}
```

### Phase 4: 성능 최적화

#### 4.1. 메모리 누수 방지
- 모든 interval/timeout 정리
- 이벤트 리스너 정리
- WeakRef 사용 검토

#### 4.2. 배터리 최적화
- Guardian 주기 조정 (2초 → 5초)
- 백그라운드에서 음성 인식 중지
- Wake Lock 사용 고려

## 🗂️ 파일별 변경 계획

### `src/lib/stt/native.ts`
- [ ] 이벤트 리스너 정리 메커니즘 추가
- [ ] 권한 상태 관리 개선
- [ ] 중복 전송 방지 로직 수정
- [ ] destroy() 메서드 추가

### `src/lib/tts/capacitor.ts`
- [ ] 에러 복구 로직 강화
- [ ] 상태 동기화 개선

### `src/routes/+page.svelte`
- [ ] VoiceController 도입으로 로직 분리
- [ ] Guardian 로직 제거 (VoiceController로 이동)
- [ ] 리소스 정리 강화

### `src/lib/stores/conversation.svelte.ts`
- [ ] 상태 전이 규칙 명확화
- [ ] 에러 상태 추가
- [ ] 복구 메커니즘 추가

### 새 파일들
- [ ] `src/lib/voice/VoiceController.ts` - 통합 관리 클래스
- [ ] `src/lib/errors/ErrorHandler.ts` - 에러 처리 클래스
- [ ] `src/lib/voice/types.ts` - 타입 정의

## 🎯 우선순위 및 타임라인

### 즉시 (Critical Fixes)
1. **STT 중복 전송 문제 해결** - 가장 심각한 UX 문제
2. **권한 처리 개선** - Guardian과의 충돌 해결
3. **메모리 누수 방지** - 안정성 개선

### 단기 (1-2일)
4. **에러 처리 강화** - 복구 메커니즘 추가
5. **상태 머신 개선** - 전이 규칙 명확화

### 중기 (1주)
6. **VoiceController 도입** - 구조 개선
7. **성능 최적화** - 배터리, 메모리 효율

## 🧪 테스트 계획

### Unit Tests
- [ ] STT 이벤트 처리 로직
- [ ] TTS 큐 관리
- [ ] 상태 머신 전이

### Integration Tests
- [ ] STT → TTS 플로우
- [ ] 권한 처리
- [ ] 에러 복구

### Device Tests (Galaxy A50)
- [ ] 장시간 사용 테스트
- [ ] 메모리 누수 모니터링
- [ ] 배터리 사용량 측정

## ⚠️ 리팩토링 주의사항

1. **점진적 적용**: 한 번에 모든 것을 바꾸지 말고 단계별로
2. **백업**: 현재 동작하는 코드 보존
3. **테스트**: 각 단계마다 실제 기기에서 검증
4. **롤백 계획**: 문제 발생 시 빠르게 되돌릴 수 있도록

## 📈 예상 효과

- **사용자 경험**: 중복 전송 해결로 대화 품질 개선
- **안정성**: 메모리 누수 방지, 에러 복구로 안정성 향상
- **유지보수성**: 구조 개선으로 코드 이해도 및 수정 용이성 향상
- **성능**: 리소스 정리로 장시간 사용 시 성능 저하 방지

---

*작성일: 2026-02-13*  
*대상 버전: voice-chat v1.0*  
*검토자: 티라노 김 (마스터)*