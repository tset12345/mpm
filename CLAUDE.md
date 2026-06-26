# MPM — Claude Code 컨텍스트

> 마지막 업데이트: 2026-06-26

---

## 프로젝트 개요

**MPM (My Portfolio Manager)** — AI 기반 한국 주식 포트폴리오 관리 앱.  
KIS API로 실시간 시세·수급을 수집하고, 듀얼 엔진 기술 분석으로 종목을 추천하며, 알고리즘 가상 거래를 시뮬레이션한다.

- **경로**: `/Users/admin/work/mpm`
- **로그인 계정**: tjdtjd89@naver.com
- **Hosting**: Render (BE) + Vercel (FE)

---

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| Frontend | Next.js 14 (App Router) + TypeScript + Tailwind CSS |
| Backend | FastAPI (Python 3.11) + uvicorn |
| Database | Supabase (PostgreSQL) |
| AI | Google Gemini 2.5 Flash Lite |
| Market API | 한국투자증권 KIS Developers Open API |
| Scheduler | APScheduler `AsyncIOScheduler` |
| Notification | Telegram Bot API |

---

## 주요 파일 경로

```
mpm/
├── CLAUDE.md                       ← 이 파일
├── FEATURES.md                     ← 기능 명세 (최신 상태 유지)
├── README.md                       ← 프로젝트 설명·구조·운영
├── UI_SPEC.md                      ← 프론트엔드 UI 컴포넌트 상세
├── TELEGRAM_BOT_PLAN.md            ← 양방향 텔레그램 봇 구현 계획 (미구현)
├── MPM.md                          ← 간략 요약
├── extract_all_trades.py           ← 가상거래 전체 체결내역 CSV 추출
├── extract_loss_trades.py          ← 가상거래 손실 체결내역 추출 (알고 개선용)
├── check.sh                        ← FE/BE 상태 확인·재시작·종료
├── dev.sh                          ← 개발 환경 통합 실행
├── backend/
│   ├── .env                        ← 환경변수 (로컬 전용, 비공개)
│   ├── API.md                      ← API 레퍼런스
│   └── app/
│       ├── core/config.py          ← pydantic-settings 환경변수 로드
│       ├── services/
│       │   ├── recommendations.py  ← 추천 알고리즘 (5조건 수급 + 듀얼 엔진)
│       │   ├── virtual_trading.py  ← 가상 거래 핵심 로직
│       │   ├── scheduler.py        ← APScheduler 잡 정의
│       │   ├── telegram.py         ← 텔레그램 알림 (추천 리포트·가상 체결)
│       │   ├── technical.py        ← 듀얼 엔진 기술 분석
│       │   ├── ichimoku.py         ← 일목균형표 계산
│       │   ├── sector_leader.py    ← 섹터 주도주 + 기술 점수
│       │   ├── ohlcv_sync.py       ← OHLCV 동기화
│       │   └── kis_api.py          ← KIS API 클라이언트
│       └── routers/
│           ├── stocks.py           ← 추천·섹터·OHLCV API
│           ├── virtual.py          ← 가상 거래 API
│           └── market.py           ← 시장 현황 API
└── frontend/src/app/
    ├── stocks/page.tsx             ← 추천 종목·섹터 주도주 (UI 최신)
    ├── virtual/page.tsx            ← 가상 거래 (체결시간 KST 표시)
    └── market/page.tsx             ← 시장 현황 (지수·주도주·히트맵)
```

---

## 로컬 개발 환경

### 서비스 시작

```bash
# 통합 실행
./dev.sh

# 서비스 관리
./check.sh                   # 상태 확인
./check.sh --reboot          # FE + BE 재시작 (caffeinate -si 슬립방지)
./check.sh --reboot --be     # 백엔드만 재시작
./check.sh --close           # 전체 종료
```

- **백엔드**: `http://localhost:8000`  
- **프론트엔드**: `http://localhost:3000` (포트 3000 고정, 3001 = ARA 프로젝트 전용)
- **Swagger**: `http://localhost:8000/docs`

### 중요: check.sh 포트 규칙

- `--reboot --be`: `lsof -ti :8000 -sTCP:LISTEN`으로만 프로세스 식별 + `caffeinate -si uvicorn` 슬립 방지
- `--reboot --fe`: **포트 3001은 절대 종료하지 않음** (ARA 프로젝트). 3000/3002/3003만 정리 후 `PORT=3000` 고정 실행

---

## 환경 변수 플래그

| 변수 | 현재 로컬 값 | Render |
|------|-------------|--------|
| `ENABLE_SCHEDULER` | `true` | `true` |
| `ENABLE_INTRADAY` | `true` | `false` |
| `ENABLE_TELEGRAM` | `true` | `false` |
| `KIS_IS_MOCK` | `false` | `false` |

> **주의**: `ENABLE_TELEGRAM=true`는 로컬 `.env`에만 설정. Render 환경변수에 없으므로 자동 비활성.

---

## 스케줄러 운영 구조

### 현재 운영 방식 (Render 파이프라인 소진 기간)

2026-06 중 Render 월별 빌드 파이프라인 분 소진 → 2026-07까지 Render 배포 불가.  
현재는 **로컬 서버에서** 스케줄러와 장중 트리거를 모두 실행.

```
로컬 Mac (caffeinate -si로 슬립 방지)
├── ENABLE_SCHEDULER=true  → 08:50/11:00/14:00/16:10 일일 동기화
└── ENABLE_INTRADAY=true   → 09:00~15:20 매 10분 장중 실시간 트리거
```

### Render 복구 후 원래 구조

```
Render BE: ENABLE_SCHEDULER=true  → 일일 동기화
로컬 Mac:  ENABLE_INTRADAY=true   → 장중 실시간 트리거
```

### 가상 거래 트리거 가격 소스

`run_daily_sync()` 에서 **`_fetch_realtime_prices()`** 를 통해 포지션 종목 전체를 KIS 실시간가로 조회 후 `virtual_sell_trigger(price_map=...)` 에 전달.  
(조건 검색 `stck_prpr`이 0이거나 전일 종가 fallback될 경우 잘못된 가격으로 매도되는 버그 수정.)

---

## 핵심 알고리즘

### 추천 알고리즘 (recommendations.py)

1. KIS 수급 조건 5종 병렬 수집 (거래대금·기관외인·거래량·신고가·VI 발동)
2. KOSPI MA20 기반 시장 국면 판단 (BULL/BEAR)
3. 130일 OHLCV + 일목균형표 + 듀얼 엔진 기술 분석 (Engine A: 추세 돌파 / Engine B: 역추세 반등)
4. 점수 임계값 이상 Top 10 선정 → `stock_recommendations` upsert

### 가상 거래 계좌 설정 (virtual_trading.py)

| 설정 | 기본값 | 설명 |
|------|--------|------|
| `strategy` | `both` | `engine_a` / `engine_b` / `both` (A 또는 B) / `both_and` (A 및 B 동시) |
| `score_filter_type` | `gte` | `gte` / `lte` / `range` |
| `min_score` / `max_score` | 50 / null | 기술 점수 필터 범위 |
| `max_hold_days` | null | 초과 시 `max_hold_exit` 강제 청산 |
| `filter_excl_large_cap` | false | 시총 임계값 초과 종목 제외 (Engine B) |
| `filter_excl_high_amount` | false | 거래대금 임계값 초과 종목 제외 (Engine B) |

### 매도 trigger_type 전체 목록

| trigger_type | 구분 | 설명 |
|---|---|---|
| `stop_loss` | 공통 | 고정 손절 |
| `take_profit` | 공통 | 고정 익절 |
| `max_hold_exit` | 공통 | 최대 보유일 초과 강제 청산 |
| `atr_hard_stop` | Engine A | 진입가 − 1.5×entry_ATR |
| `atr_trailing_stop` | Engine A | 최고가 − 2.0×현재ATR |
| `rsi_exhaustion` | Engine A | RSI 70+ → 70 이하 하향 |
| `entry_low_breach` | Engine B | 매수 당일 저가 이탈 |
| `time_limit_stop` | Engine B | 보유 5봉+ 손실 → 기회비용 청산 |
| `ma20_half_exit` | Engine B | MA20 최초 터치 → 50% 분할 익절 |
| `target_reached` | Engine B | 이격도≥102% 또는 RSI≥60 |

---

## 텔레그램 알림 (telegram.py)

`ENABLE_TELEGRAM=true` 시 로컬에서만 전송:

| 함수 | 전송 시점 |
|------|----------|
| `send_recommendation_report()` | 일일 동기화 완료 후 |
| `send_virtual_buy()` | 알고리즘 매수 체결 즉시 |
| `send_virtual_sell()` | 알고리즘 매도 체결 즉시 |

양방향 봇(커맨드 수신) 구현 계획은 `TELEGRAM_BOT_PLAN.md` 참조.

---

## 데이터베이스 주요 테이블

| 테이블 | 용도 |
|--------|------|
| `stock_recommendations` | 추천 종목 (engine_a/b_score, source_conditions, entry_price) |
| `stock_ohlcv` | 일별 OHLCV (고가·저가 포함, 130일) |
| `sector_leaders` | 섹터 주도주 캐시 (tech_score/engine_a_score/engine_b_score/tech_tags 포함) |
| `virtual_accounts` | 가상 계좌 (strategy, score_filter_type, max_hold_days, filter_excl_* 포함) |
| `virtual_positions` | 보유 포지션 (entry_atr, highest_price, half_exited, entry_low) |
| `virtual_trades` | 체결 내역 (trigger_type, pnl, created_at=timestamptz) |
| `stock_master` | KRX 전체 종목 (KOSPI 838 + KOSDAQ 1,819) |
| `recommendation_history` | 추천 히스토리 스냅샷 |
| `portfolio_analyses` | Gemini AI 포트폴리오 분석 캐시 |

RLS 전체 활성화 (`020_enable_rls.sql`) — anon 키 직접 접근 차단.

---

## 문서 업데이트 규칙

기능 추가·수정 후 반드시 다음 문서를 함께 업데이트:

- `FEATURES.md` — 기능 명세
- `backend/API.md` — API 레퍼런스
- `README.md` — 구조·운영
- `UI_SPEC.md` — 프론트엔드 컴포넌트
- `supabase/migrations/README.md` — 마이그레이션 이력

**제외**: `ANALYSIS_PROMPT.md` (AI 프롬프트 원문, 업데이트 대상 아님)

---

## 배포 규칙

1. 로컬 서버(`check.sh` 또는 브라우저)에서 기능 동작 확인 완료 후에만 `git push`
2. 여러 수정 사항을 묶어 1회 배포 (빌드 횟수 최소화)
3. Render 빌드 파이프라인 분이 소진되면 해당 월 내 배포 불가 → 로컬 운영으로 전환

> **현재 상태 (2026-06)**: Render 파이프라인 소진 → 로컬 서버에서 `ENABLE_SCHEDULER=true` + `ENABLE_INTRADAY=true` 운영 중. Render 배포 재개 시점: 2026-07.

---

## ARA 프로젝트와의 관계

MPM과 ARA는 **동일한 Supabase DB**를 공유. ARA 전용 테이블: `reports`, `keyword_subscriptions`, `analyzed_reports`.  
ARA 백엔드: `http://localhost:8001` (포트 3001 = ARA FE → check.sh에서 절대 종료 금지).
