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
│       │   └── analysis.py         # 퀀트·배당 전략 분석 엔드포인트
│       └── services/
│           ├── kis_api.py          # KIS Open API 클라이언트 (토큰·가격·OHLCV·거래량)
│           ├── gemini.py           # Gemini AI 포트폴리오 분석 서비스
│           ├── technical.py        # 기술적 지표 스코어링 엔진 (4카테고리 × 10점)
│           ├── ichimoku.py         # 일목균형표 계산 서비스
│           ├── recommendations.py  # OHLCV 기술 분석 기반 추천 종목 생성
│           ├── ohlcv_sync.py       # KIS → stock_ohlcv 테이블 동기화
│           ├── history.py          # 추천 히스토리 스냅샷 저장
│           ├── scheduler.py        # APScheduler 평일 자동 실행 (08:50/16:10 KST)
│           ├── portfolio_analysis.py # Gemini AI 포트폴리오 분석 서비스
│           ├── sell_signal.py      # 매도 신호 분석 (기술적·기본적·자산관리)
│           ├── stock_master_sync.py  # KRX 전체 상장 종목 동기화
│           ├── expected_return.py  # 기대수익률 계산
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
│       │   └── portfolio/page.tsx  # 프로필 관리 + 보유 종목 + AI 분석 + 매도 분석
│       ├── components/
│       │   ├── charts/CandleChart.tsx       # 캔들스틱 차트
│       │   └── stocks/
│       │       ├── StockRow.tsx             # 종목 행
│       │       ├── StockTable.tsx           # 종목 테이블
│       │       └── FavoriteButton.tsx       # 즐겨찾기 버튼
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
        └── 011_stock_master.sql            # stock_master 테이블 (KRX 전체 종목)
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
| `POST` | `/api/v1/stocks/sync/recommendations` | 추천 종목 수동 업데이트 (KIS API 즉시 호출) |
| `POST` | `/api/v1/stocks/sync/ohlcv` | OHLCV 수동 동기화 (종목 코드 미제공 시 거래량 상위 50개 자동 조회) |
| `POST` | `/api/v1/stocks/sync/master` | KRX 전체 상장 종목 동기화 (kind.krx.co.kr) |
| `GET` | `/api/v1/health` | 헬스체크 |

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
```

### RLS(Row Level Security) 비활성화

```sql
-- service_role 키 사용 환경에서 모든 테이블의 RLS 비활성화
ALTER TABLE stock_recommendations DISABLE ROW LEVEL SECURITY;
ALTER TABLE stock_ohlcv DISABLE ROW LEVEL SECURITY;
ALTER TABLE reports DISABLE ROW LEVEL SECURITY;
ALTER TABLE keyword_subscriptions DISABLE ROW LEVEL SECURITY;
ALTER TABLE recommendation_history DISABLE ROW LEVEL SECURITY;
ALTER TABLE holdings DISABLE ROW LEVEL SECURITY;
ALTER TABLE profiles DISABLE ROW LEVEL SECURITY;
ALTER TABLE portfolio_analyses DISABLE ROW LEVEL SECURITY;
ALTER TABLE stock_master DISABLE ROW LEVEL SECURITY;
```

> RLS를 비활성화하지 않으면 `service_role` 키를 사용하더라도 백엔드에서 테이블 읽기/쓰기가 차단될 수 있습니다.

---

## 데이터 수집 파이프라인

### 자동 수집 흐름

```
[APScheduler — 평일(월~금) KST 기준]

  시작 체크: 오늘 추천 데이터 없으면 즉시 동기화 (서버 재시작 시 1회)
  08:50 KST: 장 전 추천 종목 갱신 (전일 종가 기준)
  16:10 KST: 장 후 추천 종목 갱신 + OHLCV 동기화 + 히스토리 스냅샷

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
technical.analyze() — 4개 카테고리 × 최대 10점 = 최대 40점 → ×2.5 → 0–100점 정규화

  [A. 추세 — max 10pt]
  · MA 정배열 / 골든크로스 (MA5>MA20>MA60 또는 MA5>MA20 교차)          +2
  · MACD 상향돌파 (MACD선이 시그널선 상향 교차)                         +2
  · MACD 오실레이터 양전 (히스토그램 0선 상향 돌파)                      +1
  · 이격도 저점 (현재가 / MA20 < 97%)                                   +1
  · 강한 상승추세 (ADX ≥ 20 이상이며 +DI > −DI)                        +2
  · 일목 구름대 돌파 (현재가가 구름대 상단 위)                           +2
  · Parabolic SAR 매수전환 (SAR가 하락→상승 반전)                        +2 / 지속 +1

  [B. 모멘텀 — max 10pt]
  · RSI 과매도 탈출 (RSI < 30 → ≥ 30 회복)                             +2 / 과매도 유지 +1
  · RSI 상승 다이버전스 (주가 저점 하락 + RSI 저점 상승)                 +2
  · 스토캐스틱 과매도 탈출 (%K < 20 → ≥ 20 회복)                       +2 / 과매도 유지 +1
  · CCI 과매도 탈출 (CCI < −100 → ≥ −100 회복)                         +2
  · MFI 과매도 탈출 (MFI < 20 → ≥ 20 회복)                             +2 / 과매도 유지 +1

  [C. 변동성 / 가격패턴 — max 10pt]
  · 볼린저 하단 근접 (현재가 ≤ 하단밴드 × 1.02)                         +2
  · 볼린저 스퀴즈 상단돌파 (밴드폭 < 10% + 현재가 ≥ 상단밴드)           +2
  · 엔벨로프 하단지지 (현재가 ≤ 하단밴드 × 1.01 + 양봉)                 +2
  · 피봇 2차지지 (S2 ±1–5% 구간 + 양봉)                                 +2
  · 전고점 돌파 (21일 고점 돌파 + 거래량 MA20 × 1.5 이상)               +2
  · 눌림목 반등 (MA5>MA20 상승추세 유지 + MA20 2% 이내 저점 후 반등)     +2

  [D. 거래량 / 매집 — max 10pt]
  · OBV 상승추세 (5일 OBV 평균 > 10일 OBV 평균)                         +1
  · OBV 선행 돌파 (OBV 21일 고점 돌파, 주가는 미돌파)                    +2 / 동반돌파 +1
  · 거래량 급증 (거래량 ≥ MA20 × 2.0 + 양봉)                           +2
  · VR 과매도 반등 (VR < 70)                                             +2
  · Chaikin 0선 돌파 (Chaikin Oscillator 음→양 전환)                     +2
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
- **즐겨찾기**: 프론트엔드의 즐겨찾기 기능은 브라우저 `localStorage`에 저장 (서버 저장 없음).

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

### RLS(Row Level Security) 비활성화

Supabase의 RLS가 활성화된 상태에서 `service_role` 키를 사용하더라도 Python 클라이언트(`supabase-py`)에서 정책이 적용되어 읽기/쓰기가 차단될 수 있습니다.  
아래 SQL을 실행해 관련 테이블의 RLS를 비활성화하세요:

```sql
ALTER TABLE stock_recommendations DISABLE ROW LEVEL SECURITY;
ALTER TABLE stock_ohlcv DISABLE ROW LEVEL SECURITY;
ALTER TABLE reports DISABLE ROW LEVEL SECURITY;
ALTER TABLE keyword_subscriptions DISABLE ROW LEVEL SECURITY;
ALTER TABLE recommendation_history DISABLE ROW LEVEL SECURITY;
ALTER TABLE holdings DISABLE ROW LEVEL SECURITY;
ALTER TABLE profiles DISABLE ROW LEVEL SECURITY;
ALTER TABLE portfolio_analyses DISABLE ROW LEVEL SECURITY;
ALTER TABLE stock_master DISABLE ROW LEVEL SECURITY;
```
