# VoiceChat Server 점검 결과

**점검 시각:** 2026-02-14 22:55 KST  
**점검 결과:** ✅ **정상 동작**

---

## 1. 서버 상태 (systemd)

| 항목 | 값 |
|------|-----|
| 서비스 | `voicechat.service` — active (running) |
| 가동 시작 | 2026-02-14 12:36:06 UTC (약 1시간 19분 전) |
| PID | 501216 |
| 메모리 | 15.0M |
| CPU | 444ms |

## 2. API 엔드포인트 확인

서버 소스(`api.go`) 기준 등록된 엔드포인트:

| 엔드포인트 | 메서드 | 설명 | 상태 |
|-----------|--------|------|------|
| `/health` | GET | 헬스체크 | ✅ `{"status":"ok","instances":2}` |
| `/api/instances` | GET | 연결된 브릿지 목록 | ✅ 2개 인스턴스 반환 |
| `/api/chat` | POST | SSE 스트리밍 채팅 릴레이 | ✅ 로그상 정상 처리 |
| `/api/stt/stream` | WebSocket | STT 프록시 (vosk→ws) | 미확인 (별도 테스트 필요) |

## 3. 연결된 브릿지 인스턴스

| ID | 이름 | 상태 | 연결 시각 (UTC) |
|----|------|------|----------------|
| `bridge_1771072566863859747` | 회사 렉스 | online | 12:36:06 |
| `bridge_1771076485962261591` | 집 렉스 | online | 13:41:25 |

## 4. 앱↔서버 엔드포인트 매칭

앱(`settings.svelte.ts`) 기준:
- `serverUrl`: `https://voicechat.tyranno.xyz`
- `healthEndpoint`: `${serverUrl}/health` → `/health` ✅ 일치
- `instancesEndpoint`: `${serverUrl}/api/instances` → `/api/instances` ✅ 일치
- `chatEndpoint`: `${serverUrl}/api/chat` → `/api/chat` ✅ 일치

## 5. 최근 채팅 릴레이 로그

13:45~13:50 UTC 사이에 **12건의 채팅 요청** 모두 정상 완료:
- 모든 요청: `Starting chat relay` → `Chat request sent` → `Chat request completed`
- 실패 건수: **0건**
- 평균 처리 시간: 약 2~6초

## 6. 주의 사항

### TLS Handshake 에러 (무해)
13:55 UTC에 `212.73.148.31`에서 비정상 TLS 연결 시도 약 10회 발생.
- 스캐너/봇으로 추정 (unsupported protocols: `http/0.9`, `spdy/1~3`, `hq` 등)
- 서비스 영향 없음

## 결론

서버 완전 정상. 2개 브릿지 온라인, 채팅 릴레이 정상 동작, 앱↔서버 엔드포인트 일치.
