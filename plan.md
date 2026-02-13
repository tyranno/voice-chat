# VoiceChat 집 작업 플랜

## 현재 상태
- **App (voice-chat)**: git push 완료. VOSK WebSocket STT 플러그인 코드 완성.
- **Server (voice-chat-server)**: git push 완료. GCP VM 배포 완료 (health OK, Bridge 연결 중).
- **ClawBridge (clawdbot-service)**: 변경 없음. 회사 PC에서 정상 동작 중.

## 아키텍처 (STT 흐름)
```
[앱 마이크] → AudioRecord (16kHz PCM)
    → WebSocket (wss://voicechat.tyranno.xyz/api/stt/stream)
    → GCP 서버 STTProxy
    → 로컬 VOSK 서버 (ws://127.0.0.1:2700)
    → 인식 결과 JSON → 앱
```

## 남은 작업 (순서대로)

### 1. GCP VM에 VOSK 서버 설치 ⭐ 최우선
서버에 VOSK WebSocket 서버가 아직 없음! STT proxy가 `ws://127.0.0.1:2700`로 연결하는데, 이 서버가 필요.

```bash
ssh -i ~/.ssh/tstock.pem tyranno@34.64.164.13  # 또는 voicechat-key

# Docker로 VOSK 서버 실행 (가장 간단)
docker pull alphacep/kaldi-ko:latest
docker run -d --name vosk-server -p 2700:2700 alphacep/kaldi-ko:latest

# 또는 수동 설치:
# pip3 install vosk
# wget https://alphacephei.com/vosk/models/vosk-model-small-ko-0.22.zip
# unzip → vosk-model-small-ko-0.22/
# vosk-server --model vosk-model-small-ko-0.22 --port 2700
```

**확인:** `curl -i ws://127.0.0.1:2700` 또는 wscat으로 접속 테스트

### 2. 서버 config에 VOSK URL 추가
`/opt/voicechat/.env`에:
```
VOSK_URL=ws://127.0.0.1:2700
```
서버 코드 `config.go`에서 이 값을 읽어 `NewSTTProxy()`에 전달하는지 확인.

### 3. Android 플러그인 등록 (중요!)
`android/` 폴더는 gitignore라서 직접 작업 필요.

#### 3-1. VoskSttPlugin.java 복사
파일이 이미 있을 수 있음 (npx cap sync 시 android/ 재생성). 없으면:
- `android/app/src/main/java/com/tyranokim/voicechat/vosk/VoskSttPlugin.java` 에 배치
- 내용은 git의 최신 커밋 참고 (aaa750a) 또는 아래 경로에 백업:

#### 3-2. MainActivity.java에 플러그인 등록
`android/app/src/main/java/com/tyranokim/voicechat/MainActivity.java`:
```java
import com.tyranokim.voicechat.vosk.VoskSttPlugin;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(VoskSttPlugin.class);
        super.onCreate(savedInstanceState);
    }
}
```

#### 3-3. build.gradle 의존성
`android/app/build.gradle` repositories에:
```groovy
maven { url 'https://alphacephei.com/maven/' }
```
dependencies에:
```groovy
implementation 'com.neovisionaries:nv-websocket-client:2.14'
```
(VOSK AAR는 서버 사이드이므로 앱에는 불필요)

### 4. APK 빌드 & 테스트
```bash
cd C:\Project\88.MyProject\voice-chat
npm run build
npx cap sync android
# 위 3번 작업 확인 후:
# APK 빌드 (WSL)
```

### 5. 테스트 항목
- [ ] 앱에서 마이크 ON → 말하기 → STT 결과가 표시되는지
- [ ] 침묵 시 마이크가 꺼지지 않는지 (핵심!)
- [ ] 인식 결과가 채팅으로 전송되는지
- [ ] Bridge 연결 안정성 (60초 끊김 없는지)
- [ ] TTS 응답 재생

## 핵심 파일 위치
| 파일 | 용도 |
|------|------|
| `src/lib/stt/vosk.ts` | JS → Native 브릿지 (WebSocket STT) |
| `src/routes/+page.svelte` | 메인 UI (VoskSTT 사용) |
| `android/.../vosk/VoskSttPlugin.java` | AudioRecord → WebSocket 스트리밍 |
| (서버) `stt.go` | WebSocket proxy → VOSK 서버 |

## GCP 서버 접속 정보
- IP: `34.64.164.13`
- User: `tyranno`
- SSH Key: `~/.ssh/voicechat-key` (또는 vc-key)
- 서비스: `sudo systemctl restart voicechat`
- 로그: `sudo journalctl -u voicechat -f`
- 포트: 443 (HTTPS), 9090 (Bridge TCP)
- 환경: `/opt/voicechat/.env`
