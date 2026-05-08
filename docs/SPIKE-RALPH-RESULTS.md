# Spike: Ralph Loop Headless 실행 검증

> 일자: 2026-05-08
> 목적: voice-chat 통합(옵션 A - Bridge subprocess) 가능성 검증
> 결론: **가능. 다만 ralph-loop 플러그인의 자체 stop-hook 루프 기능은 사용 불가. 루프 로직은 Bridge가 직접 구현.**

## 0. 검증 환경

- OS: Windows 11 Pro
- Claude CLI: `C:\Users\lab\.local\bin\claude.exe` v2.1.128
- ralph-loop 플러그인: `C:\Users\lab\.claude\plugins\marketplaces\claude-plugins-official\plugins\ralph-loop\` (미설치, --plugin-dir로 격리 로드)
- spike 작업 폴더: `c:\Project\88.MyProject\voice-chat\.spike-ralph\`

## 1. 명령어 (검증 완료)

```bash
claude --print \
  --output-format stream-json \
  --verbose \
  --no-session-persistence \
  --dangerously-skip-permissions \
  --plugin-dir "<ralph-loop-plugin-path>" \
  "PROMPT"
```

**핵심 플래그**:
- `--print` : 비대화형, 응답 후 즉시 종료
- `--output-format stream-json --verbose` : 한 줄당 JSON 이벤트 (verbose 필수)
- `--no-session-persistence` : 세션 저장 안 함 (서비스 컨텍스트에서 불필요한 디스크 I/O 제거)
- `--dangerously-skip-permissions` : workspace trust dialog/권한 확인 스킵 (서비스에서 필수)
- `--plugin-dir <path>` : 플러그인 격리 로드 (사용자 글로벌 설치 불필요)
- `--bare` : **사용 불가** — `ANTHROPIC_API_KEY` 필요. OAuth/키체인을 무시함

## 2. stream-json 이벤트 타입 (실제 측정)

| Type | 빈도 | 의미 | 사용 |
|------|-----|------|------|
| `system/init` | 1 | 세션 시작, slash_commands·plugins 목록 | 초기 검증 |
| `system/hook_started` | N | 훅 시작 (SessionStart, UserPromptSubmit, Stop 등) | 진행상황 신호 |
| `system/hook_response` | N | 훅 종료 + output | (선택) 디버그 |
| `system/status` | 1+ | 상태 (`requesting` 등) | 진행상황 신호 |
| `stream_event` | many | API 스트리밍 raw 이벤트 (message_start, content_block_delta 등) | 실시간 텍스트 |
| `assistant` | N | 모델 응답 1턴 전체 (thinking + text + tool calls) | 턴 집계 |
| `rate_limit_event` | 1 | rate limit 정보 | 운영 모니터링 |
| `result/success` | 1 | **최종 결과** — `result` 필드에 텍스트, `total_cost_usd`, `num_turns`, `duration_ms` | **종료 신호** |

## 3. ralph-loop 플러그인 동작 (실측)

### 3.1 슬래시 커맨드 인식 ✅
- `slash_commands` 목록에 `ralph-loop:ralph-loop`, `ralph-loop:cancel-ralph`, `ralph-loop:help` 정상 등록
- `/ralph-loop ARGS` 형태로 입력 가능

### 3.2 자체 stop-hook 루프 ❌ (headless에서 안 됨)
- 슬래시 커맨드 본문의 ` ```! ` 자동실행 (setup-ralph-loop.sh) → **--print 모드에서 실행 안 됨**
- 증거: `.claude/ralph-loop.local.md` 상태 파일 미생성
- 모델은 `<promise>DONE</promise>`를 즉시 출력하고 단일 턴 종료 (num_turns=1)
- Stop hook 자체는 발동하지만, 상태 파일이 없으므로 통과 (no active loop)

### 3.3 결론
**ralph-loop 플러그인을 그대로 갖다 쓰는 건 불가**. 다만:
- Claude Code 기본 stream-json 출력 + 슬래시 커맨드 인프라는 정상 동작
- Bridge가 자체로 루프 제어하면서 매 iteration에 `claude --print` 호출하면 됨
- ralph-loop의 핵심 가치(`<promise>X</promise>` 패턴, max-iterations, prompt 재주입)는 Bridge에서 재구현 (단순한 Go 루프 코드)

## 4. 비용 (중요)

| 측정 | 값 |
|------|----|
| 단순 "PONG" 응답 (1턴, 플러그인 없음) | $0.31, 11K 토큰 캐시 생성 |
| ralph-loop 슬래시 커맨드 (1턴, 플러그인 로드) | $0.17 (cache_read 적용) |
| 50K 토큰 cache_creation | 매 새 세션 첫 호출에서 발생 |
| cache_read | 5분 TTL — 동일 세션 재호출 시 적용 |

**시사점**:
- iteration N회 = 첫 캐시 생성 1회 + read 캐시 N-1회
- 30-iteration Ralph 작업 추정: $0.5 ~ $2.0 (모델/길이 따라)
- **사용자 환경의 bkit 훅이 system prompt에 50K 토큰 추가**하는 게 비용 주범. 운영 시 `--bare` + API 키 또는 격리된 사용자 컨텍스트 필요

## 5. 사용자 환경 훅 오염 (운영 위험)

`--bare` 미사용 시:
- bkit 훅이 `bkit Feature Usage` 푸터를 응답 텍스트에 강제 부착
- bkit-rules가 PDCA 진입을 권유하는 텍스트 추가
- result.result 파싱 시 이런 사용자 노이즈가 섞임

**해결책 3개**:
1. **권장**: 서비스 전용 ANTHROPIC_API_KEY 발급 + `--bare` 사용 (가장 깨끗)
2. 차선: 서비스 전용 사용자 계정 + 빈 `~/.claude` (훅 없음)
3. 임시: result 파싱 시 알려진 푸터 패턴 strip (취약)

## 6. Phase 3 통합 설계 갱신

### 6.1 Bridge에서 자체 루프 구현
```go
// 의사코드
func RunRalphTask(ctx, prompt, opts) {
  workdir := mkTaskDir(taskId)
  promptFile := workdir + "/PROMPT.md"
  writeFile(promptFile, prompt)

  for i := 1; i <= opts.MaxIterations; i++ {
    sendProgress(taskId, i, "iteration started")
    result := claudePrint(workdir, promptFile)  // claude --print --plugin-dir ralph-loop
    parseStreamJson(result, func(event) {
      if event.type == "stream_event" { sendDelta(taskId, event.text) }
    })
    finalText := result.result

    if containsPromise(finalText, opts.CompletionPromise) {
      sendDone(taskId, summary, artifacts)
      return
    }
    if i == opts.MaxIterations {
      sendError(taskId, "max iterations reached")
      return
    }
    // 다음 iteration: 같은 prompt + 이전 결과를 컨텍스트에 추가
    appendIteration(promptFile, i, finalText)
  }
}
```

### 6.2 변경된 결정사항
- ❌ ralph-loop 플러그인 stop-hook 의존 → ✅ Bridge 자체 루프
- ❌ `/ralph-loop` 슬래시 커맨드 사용 → ✅ 직접 prompt 전달 (단순)
- 단, `--plugin-dir`로 ralph-loop 로드는 유지 가능 (참조용 메타정보)
  - 사실상 불필요. 제거해도 됨

### 6.3 새 prompt 템플릿
```
당신은 자율 작업 에이전트입니다.
작업: <USER_PROMPT>
현재 iteration: <N>/<MAX>
이전 iteration의 결과는 ./iter-<N-1>.md에 있습니다.
완료 조건: 작업이 완전히 끝났을 때만 출력 <promise>DONE</promise>
거짓 promise 금지 — 미완성이면 계속 작업.
```

## 7. Phase 3 다음 액션

### 우선순위 1 (구현 전 추가 검증)
- [ ] 서비스 전용 ANTHROPIC_API_KEY 발급 가능 여부 확인 (사용자)
- [ ] Windows Service 컨텍스트에서 `claude.exe` 실행 권한 확인
- [ ] 첫 iteration 캐시 50K 토큰을 30K 이하로 줄이는 system prompt 최소화 가능성

### 우선순위 2 (구현)
- [ ] clawdbot-service에 RalphTask 핸들러 추가 (bridge.go)
- [ ] voice-chat-server protocol.go에 task_* 메시지 타입 6개 추가
- [ ] voice-chat 앱에 작업 카드 UI

### 우선순위 3 (운영)
- [ ] iteration 진행상황을 task_progress로 어떻게 추출할지 (stream_event의 content_block_delta를 줄 단위로 묶어서 보낼지)
- [ ] artifact 수집: workdir 안의 새 파일을 어떻게 감지하고 [[FILE:...]] 흐름과 연결할지

## 8. 한계 및 향후 옵션 B 마이그레이션 트리거

이번 spike는 **MVP에 옵션 A 충분**임을 입증. 다만 다음 시점에 옵션 B (Claude Agent SDK) 마이그레이션 고려:
- 동시 실행 작업이 5개 이상으로 늘어나는 시점 (subprocess 관리 부담)
- 캐시 비용이 월 $50을 넘어가는 시점 (SDK는 더 정교한 캐시 제어 가능)
- 진행상황 세밀도 요구 증가 (stream-json 파싱 한계 도달)

## 9. 정리 (스파이크 산출물)

- 본 문서 (`docs/SPIKE-RALPH-RESULTS.md`)
- spike 작업 폴더: `.spike-ralph/` (gitignore 처리 권장)
- 검증된 명령어 1개 + 분석된 stream-json 이벤트 타입 7종
- Phase 3 통합 설계 갱신 사항 3건
