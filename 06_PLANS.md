# 텔레그램 봇 커맨드 수신 구현 계획

## 개요

현재 구현된 단방향 전송(스케줄 → 텔레그램)을 확장해,  
사용자가 텔레그램에서 커맨드를 전송하면 서버가 응답하는 양방향 봇 구현.

---

## 환경별 동작 분리

| 환경 | 방식 | 설정 |
|------|------|------|
| 로컬 | Long-polling (`getUpdates`) | `ENABLE_TELEGRAM_POLLING=true` |
| Render | Webhook | `TELEGRAM_WEBHOOK_SECRET=...` |

- 로컬은 공개 URL이 없어 polling 방식 사용
- Render는 공개 HTTPS URL 보유 → webhook이 효율적

---

## 추가/변경 파일

| 파일 | 작업 |
|------|------|
| `backend/app/services/telegram.py` | 커맨드 파서 + 핸들러 함수 추가 |
| `backend/app/api/v1/telegram.py` | Webhook 수신 엔드포인트 신규 (`POST /api/v1/telegram/webhook`) |
| `backend/app/services/scheduler.py` | polling 잡 추가 (로컬 전용, `ENABLE_TELEGRAM_POLLING` 게이트) |
| `backend/app/core/config.py` | `enable_telegram_polling`, `telegram_webhook_secret` 필드 추가 |
| `backend/.env` | `ENABLE_TELEGRAM_POLLING=true` 추가 |

---

## 지원 커맨드

| 커맨드 | 응답 데이터 | 데이터 소스 |
|--------|------------|------------|
| `/추천` | 오늘의 추천 종목 (현재 전송 포맷 동일) | `stock_recommendations` |
| `/가상` | 가상 계좌 수익률 요약 | `virtual_accounts`, `virtual_positions` |
| `/포지션` | 현재 보유 포지션 목록 | `virtual_positions` |
| `/시장` | KOSPI/KOSDAQ 지수 현황 | KIS API |

---

## 로컬 polling 구현 상세

```python
# scheduler.py — ENABLE_TELEGRAM_POLLING=true 시 등록
scheduler.add_job(
    poll_telegram_updates,
    CronTrigger(second="*/5"),   # 5초마다
    id="telegram_polling",
)
```

- `getUpdates?timeout=4&offset=...` long-polling
- 마지막 처리한 `update_id` 메모리 보관 (서버 재시작 시 초기화)
- 커맨드 외 일반 메시지는 무시

---

## Render 전환 시 추가 작업

1. `setWebhook` API 호출로 Webhook URL 등록
   ```
   https://{render-url}/api/v1/telegram/webhook
   ```
2. Render 환경변수: `ENABLE_TELEGRAM_POLLING=false`, `TELEGRAM_WEBHOOK_SECRET={secret}`
3. Webhook 엔드포인트에서 secret 검증 후 커맨드 처리

---

## DB 마이그레이션

불필요 — 모든 응답 데이터는 기존 테이블 및 API에서 조회.
