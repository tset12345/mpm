# MPM — My Portfolio Manager

AI 기반 한국 주식 포트폴리오 관리 시스템. 실시간 KIS API 데이터 + Gemini AI 리포트 요약.

---

## 개요

MPM은 한국투자증권(KIS) Open API로 주식 데이터를 수집하고, Google Gemini AI로 포트폴리오를 분석하는 풀스택 포트폴리오 관리 앱입니다.

- 매일 장 마감 후(16:10 KST) 4개 카테고리 기술적 분석(0–100점)으로 거래량 상위 종목을 자동 스코어링·선별
- 보유 종목을 Gemini AI로 퀀트·배당 전략별 맞춤 분석 제공
- Supabase(PostgreSQL)에 결과를 캐싱해 불필요한 API 호출 최소화

> **리포트 기능(PDF 업로드·네이버 금융 스크래핑)은 [ARA](../ara) 프로젝트로 분리되었습니다.**

---

## 기술 스택

| 구분 | 기술 | 용도 |
|------|------|------|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS | 웹 UI |
| Backend | FastAPI (Python 3.11), APScheduler | REST API, 스케줄러 |
| Database | Supabase (PostgreSQL) | 데이터 저장·캐싱 |
| AI | Google Gemini 2.5 Flash Lite | 포트폴리오 분석 |
| 증권 API | 한국투자증권 KIS Open API | 주가·OHLCV·거래량 |

---

## 프로젝트 구조

```
mpm/
├── dev.sh                          # 개발 환경 통합 실행 스크립트
├── check.sh                        # FE/BE 상태 확인 및 재시작·종료 스크립트
├── extract_all_trades.py           # 가상거래 전체 체결내역 CSV 추출 스크립트
├── extract_loss_trades.py          # 가상거래 손실 체결내역 CSV 추출 (알고리즘 개선용)
├── backend/
│   ├── requirements.txt            # Python 의존성
│   ├── .env.example                # 환경 변수 템플릿
│   └── app/
│       ├── main.py                 # FastAPI 앱 진입점, CORS, 라우터 등록
│       ├── core/
│       │   └── config.py           # pydantic-settings 기반 환경 변수 로드
│       ├── models/
│       │   └── schemas.py          # Pydantic 응답 스키마 정의
│       ├── routers/
│       │   ├── stocks.py           # 종목 추천·검색·상세·동기화 엔드포인트
│       │   ├── holdings.py         # 보유 종목 CRUD + 매도 분석 엔드포인트
│       │   ├── profiles.py         # 투자 프로필 CRUD 엔드포인트
│       │   ├── portfolio.py        # AI 포트폴리오 분석 엔드포인트
│       │   ├── analysis.py         # 퀀트·배당 전략 분석 엔드포인트
│       │   └── virtual.py          # 가상 거래 계좌·포지션·체결내역 엔드포인트
│       │   └── market.py           # 시장 현황 (지수 카드·랭킹·트리맵·지수차트·수급·ADR·스파크라인)
│       └── services/
│           ├── kis_api.py          # KIS Open API 클라이언트 (토큰·가격·OHLCV·거래량)
│           ├── gemini.py           # Gemini AI 포트폴리오 분석 서비스
│           ├── technical.py        # 듀얼 엔진 기술 분석 (Engine A 추세·Engine B 역추세, max 100pt)
│           ├── ichimoku.py         # 일목균형표 계산 서비스
│           ├── recommendations.py  # OHLCV 기술 분석 기반 추천 종목 생성
│           ├── ohlcv_sync.py       # KIS → stock_ohlcv 테이블 동기화
│           ├── history.py          # 추천 히스토리 스냅샷 저장
│           ├── scheduler.py        # APScheduler 평일 자동 실행 (08:50/11:00/14:00/16:10 KST)
│           ├── telegram.py         # 텔레그램 봇 메시지 전송 (추천 리포트, 로컬 전용)
│           ├── portfolio_analysis.py # Gemini AI 포트폴리오 분석 서비스
│           ├── sell_signal.py      # 매도 신호 분석 (기술적·기본적·자산관리)
│           ├── stock_master_sync.py  # KRX 전체 상장 종목 동기화
│           ├── expected_return.py  # 기대수익률 계산
│           ├── virtual_trading.py  # 가상 거래 트리거 (algo 매수·매도, 손절·익절)
│           ├── sector_leader.py    # 섹터 주도주 스코어링 및 KIS 조회
│           └── supabase_client.py  # Supabase Python 클라이언트 싱글턴
├── frontend/
│   ├── next.config.js
│   ├── tailwind.config.ts
│   └── src/
│       ├── app/
│       │   ├── layout.tsx          # 루트 레이아웃
│       │   ├── page.tsx            # 메인 페이지
│       │   ├── stocks/
│       │   │   ├── page.tsx        # 추천 종목 목록 + 즐겨찾기 탭 + 종목명 검색
│       │   │   ├── history/page.tsx # 추천 히스토리 (일/주/월별)
│       │   │   └── [code]/page.tsx  # 종목 상세 (PER/PBR/차트/즐겨찾기)
│       │   ├── portfolio/page.tsx  # 프로필 관리 + 보유 종목 + AI 분석 + 매도 분석
│       │   └── virtual/
│       │       └── page.tsx        # 가상 거래 (계좌 관리 + 포지션 + 체결 내역)
│       │   └── market/
│       │       └── page.tsx        # 시장 현황 (지수 차트 + 트리맵 히트맵)
│       ├── components/
│       │   ├── charts/CandleChart.tsx       # 캔들스틱 차트
│       │   └── stocks/
│       │       ├── StockRow.tsx             # 종목 행
│       │       ├── StockTable.tsx           # 종목 테이블
│       │       └── FavoriteButton.tsx       # 즐겨찾기 버튼
│   ├── market/
│   │   ├── MarketDashboard.tsx     # 8개 지수 카드 + 수급 현황 (대시보드 탭)
│   │   ├── MarketRankings.tsx      # 주도주 8개 카테고리 랭킹 (랭킹 탭)
│   │   └── TreemapHeatmap.tsx      # Squarified 트리맵 히트맵 (히트맵 탭)
│   └── LogoutButton.tsx            # 로그아웃 버튼 (네비게이션 바)
│       ├── hooks/
│       │   ├── useFavorites.ts     # 즐겨찾기 로컬스토리지 훅
│       │   └── useProfile.ts       # 투자 프로필 상태 관리 훅
│       └── lib/
│           ├── api.ts              # 백엔드 API 호출 함수 모음
│           └── types.ts            # TypeScript 인터페이스 정의
└── supabase/
    └── migrations/
        ├── 001_initial_schema.sql          # 기본 테이블 (stock_recommendations, stock_ohlcv, reports)
        ├── 002_keyword_subscriptions.sql   # keyword_subscriptions 테이블
        ├── 003_reports_matched_keywords.sql
        ├── 004_keyword_subscriptions_source_url.sql
        ├── 005_recommendation_history.sql  # recommendation_history 테이블
        ├── 006_holdings.sql                # holdings 테이블
        ├── 007_tech_score.sql              # tech_score 컬럼 추가
        ├── 008_profiles.sql                # profiles 테이블
        ├── 009_portfolio_analysis.sql      # portfolio_analyses 테이블
        ├── 010_profile_analysis_type.sql   # analysis_type 컬럼 추가
        ├── 011_stock_master.sql            # stock_master 테이블 (KRX 전체 종목)
        ├── 012_reports_source_url.sql
        ├── 013_reports_related_stocks.sql
        ├── 014_recommendations_fund_score.sql
        ├── 015_recommendations_entry_price.sql
        ├── 016_recommendations_source_conditions.sql
        ├── 017_sector_leaders.sql          # sector_leaders 테이블
        ├── 018_favorites.sql               # favorites 테이블
        ├── 019_virtual_trading.sql         # virtual_accounts, virtual_positions, virtual_trades
        └── 020_enable_rls.sql              # 전체 테이블 RLS 활성화
```

---

## 빠른 시작 (Quick Start)

### 사전 준비

| 항목 | 버전 / 링크 |
|------|------------|
| Python | 3.11 이상 |
| Node.js | 18 이상 |
| Supabase 프로젝트 | [supabase.com](https://supabase.com) |
| KIS Developers 앱키 | [apiportal.koreainvestment.com](https://apiportal.koreainvestment.com) |
| Google AI Studio API 키 | [aistudio.google.com](https://aistudio.google.com) |

### 설치 및 실행

```bash
# 1. 저장소 클론 후 프로젝트 루트로 이동
cd /path/to/mpm

# 2. 백엔드 환경 변수 파일 복사 후 값 채우기
cp backend/.env.example backend/.env
# → backend/.env 를 편집기로 열어 각 값 입력 (아래 환경 변수 섹션 참고)

# 3. DB 스키마 적용 — Supabase Dashboard > SQL Editor 에서
#    supabase/migrations/ 폴더의 SQL 파일을 001부터 번호 순서대로 실행
#    (psql 직접 연결은 Supabase 환경에 따라 제한될 수 있음)

# 4. 개발 서버 전체 실행
./dev.sh
```

실행 후:
- 백엔드 API: http://localhost:8000
- 프론트엔드: http://localhost:3000
- API 문서 (Swagger): http://localhost:8000/docs

### dev.sh 옵션

| 명령어 | 설명 |
|--------|------|
| `./dev.sh` | 백엔드 + 프론트엔드 전체 실행 |
| `./dev.sh --backend` 또는 `-b` | 백엔드(FastAPI)만 실행 (포트 8000) |
| `./dev.sh --frontend` 또는 `-f` | 프론트엔드(Next.js)만 실행 (포트 3000) |
| `./dev.sh -b -f` | 백엔드 + 프론트엔드 동시 실행 |
| `./dev.sh --help` 또는 `-h` | 도움말 출력 |

> `Ctrl+C`로 종료 시 백엔드·프론트엔드 프로세스가 자동으로 정리됩니다.

---

## 환경 변수 (.env)

파일 위치: `backend/.env`

| 변수명 | 설명 | 발급처 |
|--------|------|--------|
| `KIS_APP_KEY` | KIS Open API 앱키 | [KIS Developers](https://apiportal.koreainvestment.com) > 앱 등록 |
| `KIS_APP_SECRET` | KIS Open API 앱 시크릿 | 동일 (앱키와 함께 발급) |
| `KIS_ACCOUNT_NO` | 증권 계좌번호 (8자리-2자리) | 한국투자증권 계좌 |
| `KIS_IS_MOCK` | `false` 권장 (true 시 거래량 순위 미지원 → 폴백 동작) | — |
| `GEMINI_API_KEY` | Google Gemini API 키 | [Google AI Studio](https://aistudio.google.com) > Get API Key |
| `SUPABASE_URL` | Supabase 프로젝트 URL | [Supabase](https://supabase.com) > Project Settings > API |
| `SUPABASE_SERVICE_KEY` | Supabase service_role 키 (비공개 유지) | 동일 > service_role |
| `DATABASE_URL` | PostgreSQL 직접 연결 URL (참고용, 마이그레이션은 Dashboard에서 수동 실행) | Supabase > Project Settings > Database > Connection string |
| `ALLOWED_ORIGINS` | CORS 허용 출처 (쉼표 구분) | 기본값: `http://localhost:3000` |
| `ALLOWED_USER_EMAIL` | 허용할 사용자 이메일 (단일 사용자 화이트리스트) | 설정 시 해당 계정만 API 접근 허용 |
| `ENABLE_SCHEDULER` | 일일 동기화 스케줄러 | 기본값: `false` — Render 및 로컬 모두 `true` 설정 가능 |
| `ENABLE_INTRADAY` | 장중 10분 매매 트리거 활성화 (로컬 전용) | 기본값: `false`, 로컬에서 `true` 설정 |
| `ENABLE_TELEGRAM` | 텔레그램 추천 리포트 전송 (로컬 전용) | 기본값: `false` — 로컬에서만 `true`, Render 미설정 |
| `TELEGRAM_BOT_TOKEN` | 텔레그램 봇 API 토큰 | `@BotFather`에서 발급 |
| `TELEGRAM_CHAT_ID` | 메시지 수신 chat_id | 봇에 메시지 전송 후 `getUpdates`로 확인 |

프론트엔드 환경 변수 (`frontend/.env.local`):

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `NEXT_PUBLIC_API_URL` | 백엔드 API 주소 | `http://localhost:8000` |

---

## API 엔드포인트

### 종목 (Stocks)

| Method | Path | 설명 |
|--------|------|------|
| `GET` | `/api/v1/stocks/recommend` | 오늘의 추천 종목 목록 (DB 캐시, 최대 10개) |
| `GET` | `/api/v1/stocks/search` | 종목명 검색 (stock_master 기반, KOSPI/KOSDAQ 배지) |
| `GET` | `/api/v1/stocks/history` | 추천 히스토리 조회 (일/주/월별) |
| `GET` | `/api/v1/stocks/{stock_code}/detail` | 종목 상세 (현재가/PER/PBR/일목균형표/기술 스코어) |
| `GET` | `/api/v1/stocks/favorites` | 즐겨찾기 목록 조회 |
| `POST` | `/api/v1/stocks/favorites` | 즐겨찾기 추가 |
| `DELETE` | `/api/v1/stocks/favorites/{stock_code}` | 즐겨찾기 삭제 |
| `POST` | `/api/v1/stocks/sync/recommendations` | 추천 종목 수동 업데이트 (KIS API 즉시 호출) |
| `POST` | `/api/v1/stocks/sync/ohlcv` | OHLCV 수동 동기화 (종목 코드 미제공 시 거래량 상위 50개 자동 조회) |
| `POST` | `/api/v1/stocks/sync/master` | KRX 전체 상장 종목 동기화 (kind.krx.co.kr) |
| `GET` / `HEAD` | `/api/v1/health` | 헬스체크 |

### 보유 종목 (Holdings)

| Method | Path | 설명 |
|--------|------|------|
| `GET` | `/api/v1/holdings` | 보유 종목 목록 조회 (profile_id 필터 가능) |
| `POST` | `/api/v1/holdings` | 보유 종목 등록 |
| `PUT` | `/api/v1/holdings/{holding_id}` | 보유 종목 수정 |
| `DELETE` | `/api/v1/holdings/{holding_id}` | 보유 종목 삭제 |
| `GET` | `/api/v1/holdings/{holding_id}/sell-analysis` | 매도 분석 (기술적·기본적·자산관리 통합 점수) |

### 투자 프로필 (Profiles)

| Method | Path | 설명 |
|--------|------|------|
| `GET` | `/api/v1/profiles` | 프로필 목록 조회 |
| `POST` | `/api/v1/profiles` | 프로필 생성 (name, analysis_type: quant\|dividend) |
| `PUT` | `/api/v1/profiles/{profile_id}` | 프로필 수정 |
| `DELETE` | `/api/v1/profiles/{profile_id}` | 프로필 삭제 |

### 포트폴리오 (Portfolio)

| Method | Path | 설명 |
|--------|------|------|
| `GET` | `/api/v1/portfolio/analysis` | AI 포트폴리오 분석 결과 조회 (holdings_hash 기반 캐시) |
| `POST` | `/api/v1/portfolio/analysis` | AI 포트폴리오 분석 실행 (Gemini 2.5 Flash Lite, 프로필 유형별 프롬프트 분기) |

### 가상 거래 (Virtual)

| Method | Path | 설명 |
|--------|------|------|
| `GET` | `/api/v1/virtual/accounts` | 가상 계좌 목록 조회 (profile_id 필터 가능) |
| `POST` | `/api/v1/virtual/accounts` | 가상 계좌 생성 |
| `PATCH` | `/api/v1/virtual/accounts/{account_id}` | 가상 계좌 설정 수정 |
| `DELETE` | `/api/v1/virtual/accounts/{account_id}` | 가상 계좌 삭제 |
| `GET` | `/api/v1/virtual/accounts/{account_id}/positions` | 보유 포지션 목록 |
| `GET` | `/api/v1/virtual/accounts/{account_id}/trades` | 체결 내역 조회 |
| `GET` | `/api/v1/virtual/accounts/{account_id}/performance` | 계좌 성과 요약 |
| `POST` | `/api/v1/virtual/accounts/{account_id}/trades` | 수동 매매 체결 |

### 시장 현황 (Market)

| Method | Path | 설명 |
|--------|------|------|
| `GET` | `/api/v1/market/indices` | 8개 지수 현재값 (KOSPI/KOSDAQ/NASDAQ/다우/S&P500/USD-KRW/WTI/미국10년물, 1분 캐시) |
| `GET` | `/api/v1/market/rankings` | 주도주 8개 카테고리 랭킹 (상승률·하락률·거래량·거래대금·외인·기관·52주신고가·신저가, 2분 캐시) |
| `GET` | `/api/v1/market/treemap` | 트리맵 히트맵 데이터 (3분 캐시, `sort` 파라미터) |
| `GET` | `/api/v1/market/index-chart` | KOSPI/KOSDAQ 지수 차트 (`market`, `period` 파라미터) |
| `GET` | `/api/v1/market/investor-trend` | 기관·외국인·개인 수급 집계 |
| `GET` | `/api/v1/market/adr` | 등락비율(ADR) 시계열 (`days` 파라미터) |
| `GET` | `/api/v1/market/sparkline/{code}` | 종목 스파크라인 (최근 N일 종가) |

전체 API 상세 스펙은 [backend/API.md](backend/API.md) 또는 http://localhost:8000/docs (Swagger UI) 참조.

> **리포트 API**는 ARA 프로젝트(http://localhost:8001)로 분리되었습니다.

---

## 데이터베이스 스키마

### stock_recommendations — 일별 추천 종목 캐시

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | SERIAL PK | — |
| `stock_code` | VARCHAR(6) | 종목 코드 (예: `005930`) |
| `stock_name` | VARCHAR(100) | 종목명 |
| `current_price` | INTEGER | 현재가 (원) |
| `change_rate` | DECIMAL(6,2) | 등락률 (%) |
| `volume` | BIGINT | 누적 거래량 |
| `tags` | JSONB | 선정 이유 (`["골든크로스", "MACD 상향돌파", "전고점 돌파"]` 등) |
| `date` | DATE | 수집일 (기본값: 오늘) |

UNIQUE 제약: `(stock_code, date)` — 매일 종목당 1개 레코드.

### stock_ohlcv — 일별 OHLCV (2년치 보관)

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | SERIAL PK | — |
| `stock_code` | VARCHAR(6) | 종목 코드 |
| `trade_date` | DATE | 거래일 |
| `open_price` | INTEGER | 시가 |
| `high_price` | INTEGER | 고가 |
| `low_price` | INTEGER | 저가 |
| `close_price` | INTEGER | 종가 |
| `volume` | BIGINT | 거래량 |

UNIQUE 제약: `(stock_code, trade_date)` — upsert로 중복 방지.  
자동 삭제: `delete_old_ohlcv()` 함수로 2년 초과 데이터 제거.

### reports — AI 요약 리포트

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | SERIAL PK | — |
| `file_hash` | VARCHAR(64) UNIQUE | MD5 해시 — 동일 PDF 중복 업로드 방지 |
| `title` | VARCHAR(500) | 파일명에서 자동 추출 |
| `publisher` | VARCHAR(200) | 발행사 (선택) |
| `publish_date` | DATE | 발행일 (선택) |
| `target_stock_code` | VARCHAR(6) | 대상 종목 코드 (선택) |
| `raw_text` | TEXT | PDF 추출 원문 |
| `ai_summary` | JSONB | Gemini 요약 (`one_line`, `key_points`, `keywords`) |
| `created_at` | TIMESTAMPTZ | 업로드 시각 |

### recommendation_history — 추천 히스토리 스냅샷

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | SERIAL PK | — |
| `period_type` | VARCHAR(10) | `daily` / `weekly` / `monthly` |
| `period_key` | VARCHAR(20) | 기간 식별자 (예: `2026-05-18`, `2026-W20`, `2026-05`) |
| `stocks` | JSONB | 해당 기간 추천 종목 배열 |
| `created_at` | TIMESTAMPTZ | 스냅샷 생성 시각 |

UNIQUE 제약: `(period_type, period_key)`.

### keyword_subscriptions — 키워드 구독

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | SERIAL PK | — |
| `keyword` | VARCHAR(100) | 구독 키워드 또는 종목코드 |
| `source_url` | TEXT | 연결된 리포트 URL (선택) |
| `created_at` | TIMESTAMPTZ | 등록 시각 |

### holdings — 보유 종목

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | SERIAL PK | — |
| `profile_id` | INTEGER FK | 연결된 투자 프로필 |
| `stock_code` | VARCHAR(6) | 종목 코드 |
| `stock_name` | VARCHAR(100) | 종목명 |
| `avg_price` | DECIMAL(12,2) | 평균 매입단가 |
| `quantity` | INTEGER | 보유 수량 |
| `memo` | TEXT | 메모 (선택) |
| `created_at` | TIMESTAMPTZ | 등록 시각 |

### profiles — 투자 프로필

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | SERIAL PK | — |
| `name` | VARCHAR(100) | 프로필명 |
| `analysis_type` | VARCHAR(20) | `quant` (퀀트) 또는 `dividend` (배당) |
| `created_at` | TIMESTAMPTZ | 생성 시각 |

### portfolio_analyses — AI 포트폴리오 분석 캐시

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | SERIAL PK | — |
| `profile_id` | INTEGER FK | 연결된 투자 프로필 |
| `holdings_hash` | VARCHAR(64) | 보유 종목 구성 해시 — 변경 감지용 |
| `analysis` | JSONB | Gemini AI 분석 결과 |
| `created_at` | DATE | 분석 날짜 (일 1회 캐시) |

UNIQUE 제약: `(profile_id, holdings_hash, created_at)`.

### stock_master — KRX 전체 상장 종목

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | SERIAL PK | — |
| `stock_code` | VARCHAR(6) UNIQUE | 종목 코드 |
| `stock_name` | VARCHAR(100) | 종목명 |
| `market` | VARCHAR(10) | `KOSPI` 또는 `KOSDAQ` |
| `updated_at` | TIMESTAMPTZ | 최종 동기화 시각 |

KOSPI 838건 + KOSDAQ 1,819건 = 약 2,657건 보관.

### favorites — 즐겨찾기 종목

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `stock_code` | VARCHAR(10) PK | 종목 코드 |
| `stock_name` | TEXT | 종목명 |
| `created_at` | TIMESTAMPTZ | 등록 시각 |

### virtual_accounts — 가상 거래 계좌

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | SERIAL PK | — |
| `profile_id` | INTEGER FK | 연결된 투자 프로필 (ON DELETE CASCADE) |
| `name` | TEXT | 계좌명 |
| `initial_cash` | INTEGER | 초기 자금 (원, 기본 1,000만) |
| `current_cash` | INTEGER | 현재 잔고 |
| `strategy` | TEXT | 전략 (`engine_a` / `engine_b` / `both`) |
| `min_score` | INTEGER | 매수 최소 기술 점수 (기본 50) |
| `max_positions` | INTEGER | 최대 보유 종목 수 (기본 5) |
| `position_size` | INTEGER | 종목당 투자 비율 % (기본 20) |
| `stop_loss_pct` | INTEGER | 손절 기준 % (기본 10) |
| `take_profit_pct` | INTEGER | 익절 기준 % (기본 20) |
| `is_active` | BOOLEAN | 활성 여부 |
| `created_at` | TIMESTAMPTZ | 생성 시각 |

### virtual_positions — 가상 보유 포지션

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | SERIAL PK | — |
| `account_id` | INTEGER FK | 연결된 가상 계좌 |
| `stock_code` | TEXT | 종목 코드 |
| `stock_name` | TEXT | 종목명 |
| `quantity` | INTEGER | 보유 수량 |
| `avg_price` | INTEGER | 평균 매입가 |
| `entry_date` | DATE | 매수일 |
| `entry_score` | INTEGER | 매수 시점 기술 점수 |
| `engine` | TEXT | 매수 엔진 (`A` / `B`) |
| `entry_atr` | INTEGER | 매수 시점 ATR (Engine A ATR 스탑 계산용) |
| `highest_price` | INTEGER | 보유 중 최고가 (Engine A 트레일링 스탑 기준) |
| `half_exited` | BOOLEAN | Engine B MA20 분할 익절 완료 여부 (기본 false) |
| `entry_low` | INTEGER | 매수 당일 저가 (Engine B 진입 저점 손절 기준) |

UNIQUE 제약: `(account_id, stock_code)`.

### virtual_trades — 가상 체결 내역

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | SERIAL PK | — |
| `account_id` | INTEGER FK | 연결된 가상 계좌 |
| `stock_code` | TEXT | 종목 코드 |
| `stock_name` | TEXT | 종목명 |
| `side` | TEXT | `buy` / `sell` |
| `quantity` | INTEGER | 체결 수량 |
| `price` | INTEGER | 체결가 |
| `amount` | INTEGER | 체결금액 (price × quantity) |
| `trigger_type` | TEXT | 매수: `algo_buy`/`manual` · 매도(공통): `stop_loss`/`take_profit` · 매도(A): `atr_hard_stop`/`atr_trailing_stop`/`rsi_exhaustion` · 매도(B): `entry_low_breach`/`time_limit_stop`/`ma20_half_exit`/`target_reached` |
| `engine` | TEXT | 엔진 (`A` / `B`) |
| `tech_score` | INTEGER | 체결 시 기술 점수 |
| `sell_score` | INTEGER | 매도 신호 점수 (매도 시) |
| `pnl` | INTEGER | 실현손익 (매도 시, 매수 시 NULL) |
| `pnl_rate` | NUMERIC(7,2) | 수익률 (%) |
| `traded_at` | DATE | 체결일 |

---

## 데이터베이스 마이그레이션

> **운영 방식**: Supabase는 외부에서 psql 직접 연결이 제한될 수 있습니다. 현재 마이그레이션은 **Supabase Dashboard > SQL Editor**에서 각 파일 내용을 직접 붙여넣어 수동 실행하는 방식으로 운영됩니다.

### 마이그레이션 순서

`supabase/migrations/` 폴더의 SQL 파일을 번호 순서대로 Supabase SQL Editor에서 실행하세요.

```
001_initial_schema.sql          → stock_recommendations, stock_ohlcv, reports
002_keyword_subscriptions.sql   → keyword_subscriptions
003_reports_matched_keywords.sql
004_keyword_subscriptions_source_url.sql
005_recommendation_history.sql  → recommendation_history
006_holdings.sql                → holdings
007_tech_score.sql              → tech_score 컬럼
008_profiles.sql                → profiles
009_portfolio_analysis.sql      → portfolio_analyses
010_profile_analysis_type.sql   → analysis_type 컬럼
011_stock_master.sql            → stock_master
012_reports_source_url.sql
013_reports_related_stocks.sql
014_recommendations_fund_score.sql
015_recommendations_entry_price.sql
016_recommendations_source_conditions.sql
017_sector_leaders.sql          → sector_leaders
018_favorites.sql               → favorites
019_virtual_trading.sql         → virtual_accounts, virtual_positions, virtual_trades
020_enable_rls.sql              → 전체 테이블 RLS 활성화
021_virtual_position_tracking.sql → virtual_positions에 entry_atr·highest_price·half_exited·entry_low 추가
```

### RLS(Row Level Security)

모든 테이블에 RLS가 활성화되어 있습니다(`020_enable_rls.sql`).

- **백엔드(service_role 키)**: RLS를 자동으로 우회 — 별도 정책 불필요
- **Supabase anon 키(프론트엔드)**: 정책 없음 = 기본 거부(default-deny) — PostgREST 직접 접근 차단
- **보안 효과**: 공개 anon 키(`NEXT_PUBLIC_SUPABASE_ANON_KEY`)로 DB에 직접 읽기·쓰기 불가

추가 보안 계층:

| 계층 | 조치 |
|------|------|
| API 인증 | Supabase JWT(Bearer) 검증 (`app/core/auth.py`) |
| 사용자 화이트리스트 | `ALLOWED_USER_EMAIL` 설정 시 해당 계정만 허용 |
| CORS | `ALLOWED_ORIGINS` 설정 도메인만 허용 |
| JWKS TTL | 1시간마다 공개키 재조회 (키 로테이션 대응) |

---

## 데이터 수집 파이프라인

### 자동 수집 흐름

```
[APScheduler — 평일(월~금) KST 기준]

  시작 체크: 오늘 추천 데이터 없으면 즉시 동기화 (서버 재시작 시 1회)
  08:50 KST: 장 전 추천 종목 갱신 (전일 종가 기준)
  09:05 KST: 섹터 주도주 전체 20개 갱신
  11:00 KST: 오전 장중 추천 종목 갱신 + 가상 거래 트리거
  14:00 KST: 오후 장중 추천 종목 갱신 + 가상 거래 트리거
  16:10 KST: 장 후 추천 종목 갱신 + OHLCV 동기화 + 히스토리 스냅샷 + 가상 거래 트리거

  가상 거래 트리거 순서: virtual_sell_trigger() → virtual_buy_trigger()
  (손절·익절·매도신호 먼저 처리 후 신규 매수)

[16:10 KST 장 후 동기화 상세]
        │
        ▼
KIS API: get_volume_ranking()
거래량 순위 상위 종목 조회 (실서버 전용, 평일 16:10 KST)
        │
        ▼
ETF/ETN 자동 제외
  ├─ 종목 코드에 영문자 포함 시 제외 (ETN)
  └─ 종목명에 KODEX/TIGER/KINDEX/레버리지/인버스/2X 등 키워드 포함 시 제외 (ETF)
        │
        ▼
상위 30개 종목 130일 OHLCV 병렬 수집 (asyncio.Semaphore=5, KIS rate limit 방지)
        │
        ├─ KIS API 실패 시 → FALLBACK_STOCKS(주요 10종목) 사용
        │
        ▼
technical.analyze() — 듀얼 엔진 스코어링, score = max(engine_a, engine_b), 0–100점

  [Stage 1 — Hard Filter]
  · MA20 거래량 < 100,000주 → 즉시 탈락 (score=0)

  [Engine A — 추세 돌파형, max 100pt]
  BEAR 시장 (KOSPI < MA20) → 즉시 0점
  · 골든크로스 (MA5>MA20>MA60 정배열 → 15 / MA5>MA20만 → 8)           max 15
  · ADX/DMI 강한 상승추세 (ADX≥25 → 15 / ADX≥20 → 10)                max 15
  · 일목 구름대 돌파 (above_cloud → 15 / in_cloud → 5)                  max 15
  · 볼린저 스퀴즈 상단돌파 (밴드폭<10%+상단≥ → 15 / 밴드폭<10%+중간> → 6) max 15
  · 전고점 돌파 (21일 고점+거래량≥1.5× → 15 / 거래량 미충족 → 8)       max 15
  · OBV 선행 돌파 (OBV>고점+주가≤고점 → 15 / OBV>고점만 → 8)          max 15
  · 거래량 급증 (≥3.0×+양봉 → 10 / ≥2.0× → 7 / ≥1.5× → 3)           max 10
  · RSI Hard Veto: ≥80 → 즉시 0점
  · RSI 최초 70 돌파 (직전<70): +5
  · RSI 지속 70+: max(0, score−10)

  [Engine B — 역추세 반등형, max 100pt]
  Pre-filter: 거래대금<50억 또는 MA60 우하향 → 즉시 0점
  B1 (disparity < 99): (이격도 + 과매도 + 수요밴드) / 75 × 100
  · 이격도 저점 (<93%→15 / <95%→12 / <97%→8 / <99%→3)               max 15
  · 과매도 그룹 RSI/Stoch/CCI/MFI (≥3개→25 / ≥2개→20 / 1개→10)       max 25
  · 수요밴드 통합 (볼린저하단·엔벨로프하단·피봇S2·피보나치,
    ≥2개+양봉→35 / ≥2개→20 / 1개+양봉→20 / 1개→8)                    max 35
  B2 (disparity ≥ 99): (과매도 + 수요밴드 + 눌림목) / 85 × 100
  · 눌림목 반등 (MA5>MA20+MA20터치+양봉→25 / 양봉 미충족→12)           max 25
        │
        ▼
기술 스코어 내림차순 정렬 → 상위 10개 선택
보조 태그 추가: 등락률 3%↑ → "등락률 급등", 52주 신고가 95% 근접 → "52주 신고가 근접"
        │
        ▼
stock_recommendations 테이블 저장 (오늘 날짜 기존 데이터 삭제 후 재삽입)
```

### KIS_IS_MOCK 동작 차이

| 항목 | 모의투자 (`KIS_IS_MOCK=true`) | 실서버 (`KIS_IS_MOCK=false`) |
|------|-------------------------------|-------------------------------|
| API 서버 | `openapivts.koreainvestment.com:29443` | `openapi.koreainvestment.com:9443` |
| 거래량 순위 (`get_volume_ranking`) | 지원하지 않아 폴백 데이터 사용 | 정상 동작 |
| 주가 조회 (`get_stock_price`) | 모의투자 시세 반환 | 실시간 시세 반환 |
| OHLCV 조회 (`get_daily_ohlcv`) | 모의투자 데이터 반환 | 실제 차트 데이터 반환 |
| 추천 종목 | FALLBACK_STOCKS 10개 고정 반환 | 실제 거래량 기반 필터링 |
| 권장 용도 | 개발·테스트 | 프로덕션 |

> **권장**: `KIS_IS_MOCK=false`(실서버)로 설정해야 거래량 순위 API가 정상 동작하고 실제 추천 종목이 생성됩니다.  
> `KIS_IS_MOCK=true`(모의투자)로 설정하면 거래량 순위 API를 지원하지 않아 FALLBACK_STOCKS 10개 고정 종목이 사용됩니다.

---

## 비용 최적화

| 항목 | 전략 |
|------|------|
| **Gemini API** | 동일 보유 구성(holdings_hash 일치)은 재호출 없이 DB 캐시 반환. 구성 변경 시만 API 호출. |
| **KIS API** | 장 마감 후 1회만 수집(16:10 KST 스케줄), 이후 요청은 DB에서 제공. |
| **Supabase** | OHLCV는 2년치만 보관. `delete_old_ohlcv()` 함수로 자동 정리. |
| **Rate limit** | OHLCV 종목 간 0.5초 딜레이로 KIS API 속도 제한 준수. |

---

## 개발 팁

- **API 문서**: 서버 실행 후 http://localhost:8000/docs (Swagger UI) 또는 http://localhost:8000/redoc
- **로그**: `uvicorn` 실행 시 터미널에 INFO 레벨 로그 출력. 스케줄러 실행·동기화 완료도 확인 가능.
- **수동 동기화**: 스케줄 대기 없이 즉시 데이터를 채우려면 `POST /api/v1/stocks/sync/recommendations` 호출.
- **즐겨찾기**: Supabase `favorites` 테이블에 저장 — 로컬/배포 환경 모두 동일한 목록 공유.

### check.sh — 서비스 관리 스크립트

```bash
./check.sh                  # FE + BE 상태 확인
./check.sh --be             # 백엔드만 확인
./check.sh --fe             # 프론트엔드만 확인
./check.sh --reboot         # FE + BE 재시작 후 확인
./check.sh --reboot --be    # 백엔드만 재시작 (caffeinate -si 슬립 방지 포함)
./check.sh --reboot --fe    # 프론트엔드만 재시작 (PORT=3000 고정)
./check.sh --close          # FE + BE 전체 종료
./check.sh --close --be     # 백엔드만 종료
./check.sh --close --fe     # 프론트엔드만 종료
```

> **참고**: `--reboot --be` 는 `caffeinate -si` 로 uvicorn을 감싸 Mac 유휴·시스템 슬립을 방지합니다. 덮개를 닫지 않는 환경에서 스케줄러(08:50/11:00/14:00/16:10 KST)가 안정적으로 실행됩니다.

---

### 가상거래 데이터 추출 스크립트

`backend/.env`의 `SUPABASE_SERVICE_KEY`를 사용해 직접 DB 조회 후 CSV 출력.

```bash
# 전체 체결내역 추출 (virtual_all_trades_YYYYMMDD_HHMMSS.csv)
python3 extract_all_trades.py

# 손실 체결내역만 추출 (virtual_loss_trades_YYYYMMDD_HHMMSS.csv)
python3 extract_loss_trades.py
```

출력 항목:
- `extract_all_trades.py`: 계좌명, 거래일, 구분(매수/매도), 종목, 체결가, 수량, 금액, 손익, 거래유형, 엔진, 점수, 보유일수 + 통계(승률·매도유형별 집계)
- `extract_loss_trades.py`: 손실 매도 건만 필터링 → 알고리즘 개선을 위한 분석 데이터

---

## 트러블슈팅

### KIS 토큰 파일 캐싱

KIS API 토큰은 `.kis_token_cache.json` 파일에 캐싱되어 uvicorn 재시작 후에도 유지됩니다. 토큰 만료 300초 전에 자동으로 재발급합니다.

- 캐시 파일 위치: `backend/.kis_token_cache.json`
- 캐시 파일을 삭제하면 다음 API 호출 시 토큰이 새로 발급됩니다.
- 환경(모의투자 ↔ 실서버)을 전환할 때는 캐시 파일을 삭제하세요 (base_url이 달라 자동 무효화되지만 명시적 삭제 권장).

### Supabase `ilike` 이슈

Supabase PostgREST에서 `ilike` 연산자를 사용하면 특정 버전에서 호환성 문제가 발생할 수 있습니다.  
현재 `GET /api/v1/reports/summary`의 키워드 필터링은 DB 레벨 `ilike` 대신 Python 서버사이드에서 처리합니다.  
날짜 범위 필터(`gte`, `lte`)는 정상적으로 DB 레벨에서 처리합니다.

### RLS(Row Level Security)

모든 테이블에 RLS가 활성화되어 있습니다(`020_enable_rls.sql`). `service_role` 키는 RLS를 자동으로 우회하므로 백엔드 동작에 영향 없습니다.

별도 정책을 추가하지 않으면 anon 키로는 모든 테이블이 기본 거부(default-deny)되어 PostgREST 직접 접근이 차단됩니다. 이는 의도된 보안 설정입니다.
