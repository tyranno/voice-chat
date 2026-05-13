# NanoPi 서버 - 현황 및 작업 목록

> 최종 갱신: 2026-05-14
> GCP → NanoPi M4 마이그레이션 **완료**. 이제 서버는 NanoPi 단독 운영.

---

## 서버 접속 정보

| 항목 | 값 |
|---|---|
| 장비 | NanoPC-T4 (RK3399 ARM64) |
| OS | Ubuntu 24.04 Noble Core (kernel 4.19) |
| IP (LAN) | 192.168.123.200 |
| User | tyranno / **tyranno1q2w3e4r** |
| User | pi / **tyranno1q2w3e4r** |
| SSH (외부) | `ssh nanopi` (Cloudflare Tunnel, 키 인증) |
| SSH (LAN) | `ssh nanopi-lan` 또는 `ssh tyranno@192.168.123.200` |

> ⚠️ **2026-05-14 암호 변경**: pi/tyranno 모두 `tyranno1q2w3e4r` 으로 변경됨 (브루트포스 방어)
> fail2ban 설치됨 — SSH 3회 실패 시 24시간 차단 (로컬망 192.168.123.x 제외)

---

## SSH config (집 PC 기준)

`~/.ssh/config`:
```
Host nanopi
  HostName ssh.tyranno.xyz
  User tyranno
  ProxyCommand "C:\Program Files (x86)\cloudflared\cloudflared.exe" access ssh --hostname ssh.tyranno.xyz
Host nanopi-lan
  HostName 192.168.123.200
  User tyranno
```

---

## 현재 서비스 상태 (2026-05-14 기준 모두 active)

| 서비스 | 포트 | 설명 |
|---|---|---|
| voicechat | 8090 | 메인 서버 |
| cloudflared | — | Cloudflare Tunnel |
| openclaw-gateway | 18789 (loopback) | openclaw 게이트웨이 |
| oc-proxy | 18790 | openclaw 프록시 (18789 → 18790) |
| fail2ban | — | SSH 브루트포스 차단 |

외부 접속:
- `https://voicechat.tyranno.xyz` → 8090
- `https://openclaw.tyranno.xyz` → 18789

---

## 주요 파일 위치 (NanoPi)

```
/opt/voicechat/              - 서버 바이너리 + 데이터
/opt/voicechat/.env          - 환경변수
/data/                       - SD카드 (mmcblk1, ext4, 28GB) 저장소
/etc/systemd/system/         - 서비스 파일들
/etc/cloudflared/config.yml  - Cloudflare Tunnel 설정
/home/tyranno/.cloudflared/  - Tunnel 인증서
/home/tyranno/.openclaw/     - openclaw 설정/디바이스 정보
/home/tyranno/tools/         - stock-screener, stock-picker
/etc/fail2ban/jail.local     - fail2ban SSH 설정
```

---

## 주요 명령어

```bash
sudo systemctl status voicechat cloudflared openclaw-gateway oc-proxy
sudo journalctl -u voicechat -f
sudo fail2ban-client status sshd   # 차단 현황
```

---

## ✅ 완료된 마이그레이션 작업 (2026-05-14)

| 작업 | 상태 |
|---|---|
| Ubuntu 24.04 eFlasher SD→eMMC 설치 | ✅ |
| WiFi 고정 IP (192.168.123.200) 설정 | ✅ |
| tyranno 계정 생성 + sudo | ✅ |
| Node.js 22, yt-dlp, deno, cloudflared 설치 | ✅ |
| GCP 백업 복원 (voicechat, openclaw, cloudflared, lottery) | ✅ |
| crontab 복원 | ✅ |
| systemd 서비스 등록 (voicechat, cloudflared, openclaw-gateway, oc-proxy) | ✅ |
| Cloudflare Tunnel 설정 (voicechat + openclaw 두 도메인) | ✅ |
| SD카드 /data 마운트 (mmcblk1, ext4, 28GB) | ✅ |
| openclaw allowedOrigins 추가 (https://openclaw.tyranno.xyz) | ✅ |
| openclaw 디바이스 페어링 (핸드폰) | ✅ |
| tools/ 업로드 (stock-screener, stock-picker) | ✅ |
| GCP 서비스 중지 + 프로젝트 삭제 | ✅ |
| 계정 암호 변경 (pi, tyranno → tyranno1q2w3e4r) | ✅ |
| fail2ban 설치 (SSH 브루트포스 차단) | ✅ |

---

## 남은 작업 / 확인 필요

- [ ] STT (VOSK) — 현재 Web Speech API 폴백으로 동작 중, VOSK 서버 설치하면 오프라인 STT 가능
- [ ] journald 로그 캡 설정 (`SystemMaxUse=100M`) — 장기 운영 대비
- [ ] 정기 백업 cron — `/data`나 외부에 voicechat 데이터 정기 백업 설정
