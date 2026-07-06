# MPM Backend API Reference

## 기본 정보

| 항목 | 값 |
|------|-----|
| Base URL | `http://localhost:8000` |
| API 버전 접두어 | `/api/v1` |
| 응답 형식 | `application/json` |
| 인증 | Supabase JWT Bearer 토큰 필수 (`Authorization: Bearer <token>`) |
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |

## 인증 (Authentication)

모든 엔드포인트는 Supabase JWT Bearer 토큰을 요구합니다 (`/api/v1/health` 제외).

```
Authorization: Bearer <supabase_access_token>
```

**토큰 검증 흐름** (`app/core/auth.py`):

1. JWT 헤더의 `alg` 확인
2. `ES256` 알고리즘: JWKS 엔드포인트에서 공개키 조회 후 검증 (1시간 캐시)
3. `HS256` 알고리즘: `SUPABASE_JWT_SECRET`으로 검증
4. `ALLOWED_USER_EMAIL` 설정 시 — payload의 `email`이 일치해야 접근 허용 (단일 사용자 화이트리스트)

**오류 응답**

| 상태코드 | 사유 |
|----------|------|
| 401 | 토큰 없음 / 만료 / 유효하지 않은 토큰 |
| 403 | 이메일 화이트리스트 불일치 |

### 공통 응답 구조

성공 시:
```json
{
  "status": "success",
  "data": { ... }
}
```

오류 시 (FastAPI 기본 형식):
```json
{
  "detail": "오류 메시지"
}
```

---

## 헬스체크

### GET /api/v1/health

서버 동작 여부를 확인합니다.

**응답 예시**

```json
{
  "status": "ok"
}
```

| 상태코드 | 의미 |
|----------|------|
| 200 | 서버 정상 동작 |

---

## 종목 (Stocks)

### GET /api/v1/stocks/recommend

오늘의 추천 종목 목록을 반환합니다. `stock_recommendations` 테이블에서 가장 최근 날짜의 종목을 `tech_score` 내림차순으로 반환합니다.

**Query Parameters**: 없음

**응답 예시**

```json
{
  "status": "success",
  "date": "2026-05-15",
  "data": [
    {
      "id": 1,
      "stock_code": "005930",
      "stock_name": "삼성전자",
      "current_price": 74200,
      "change_rate": 2.35,
      "volume": 14250300,
      "tech_score": 82,
      "tags": ["A추세상승", "B모멘텀강세", "등락률 급등"],
      "date": "2026-05-15",
      "created_at": "2026-05-15T16:03:12.000Z"
    }
  ]
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `date` | string \| null | 최신 데이터 기준일 (YYYY-MM-DD) |
| `data[].stock_code` | string | 종목 코드 (6자리) |
| `data[].stock_name` | string | 종목명 |
| `data[].current_price` | integer | 현재가 (원) |
| `data[].change_rate` | number | 전일 대비 등락률 (%) |
| `data[].volume` | integer | 누적 거래량 |
| `data[].tech_score` | integer | 기술적 분석 점수 (0–100) |
| `data[].tags` | string[] | 선정 이유 태그 |

**비고**

- 매일 16:10 KST 자동 갱신. 당일 데이터가 없으면 전날 데이터가 반환될 수 있습니다.
- DB 조회 실패 시 HTTP 200으로 `data: []` 반환.

| 상태코드 | 의미 |
|----------|------|
| 200 | 정상 (데이터 없을 때도 200, `data: []`) |

---

### GET /api/v1/stocks/recommend/prices

추천 종목의 현재가·등락률만 KIS API에서 실시간 조회합니다. 프론트엔드에서 30초마다 폴링해 화면을 갱신할 때 사용합니다.

**Query Parameters**: 없음

**응답 예시**

```json
{
  "status": "success",
  "data": [
    {
      "stock_code": "005930",
      "current_price": 74200,
      "change_rate": 2.35
    }
  ]
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `data[].stock_code` | string | 종목 코드 |
| `data[].current_price` | number \| null | 현재가 (원) |
| `data[].change_rate` | number \| null | 전일 대비 등락률 (%) |

| 상태코드 | 의미 |
|----------|------|
| 200 | 정상 |

---

### GET /api/v1/stocks/sector-leader

지정한 섹터의 주도주 상위 3개를 반환합니다. 기본적으로 `sector_leaders` 테이블 캐시를 우선 조회하며, `force=true` 시 KIS API를 재조회하고 캐시를 갱신합니다.

**Query Parameters**

| 파라미터 | 타입 | 필수 | 기본값 | 설명 |
|----------|------|------|--------|------|
| `sector` | string | 예 | — | 섹터명 (예: `반도체(AI/HBM)`) |
| `force` | boolean | 아니오 | `false` | `true` 시 KIS API 재조회 후 캐시 갱신 |

**지원 섹터 (20개)**

반도체(AI/HBM), 온디바이스 AI, 2차전지 소재·장비, 로봇·스마트팩토리, 우주항공·방산, 자율주행·전장부품, 바이오시밀러·신약, 양자컴퓨터·원자력(SMR), 자동차 제조, 조선·해양플랜트, 철강·비철금속, 화학·정유, 디스플레이·OLED, 기계·건설장비, 인터넷·엔터테인먼트, 게임·콘텐츠, 금융(은행·보험·증권), 음식료, 화장품·미용기기, 신재생 에너지

**처리 로직 (force=false)**

1. `sector_leaders` 테이블에서 해당 섹터 캐시 조회
2. 캐시 있으면 즉시 반환 / 없으면 빈 배열 반환 (자동 조회 없음)

**처리 로직 (force=true)**

1. 섹터 내 종목 코드 조회 (하드코딩 매핑)
2. KIS API `get_stock_price()` 호출 — 글로벌 세마포어(5) 적용으로 동시 호출 상한 제어
3. `stock_master` DB에서 종목명 일괄 조회
4. `stock_ohlcv` DB에서 최근 130일 OHLCV(고가·저가·종가·거래량) → MA5 / MA20 / MA60 계산
5. 시가총액 500억 미만 Hard Filter 제외
6. 섹터 스코어링(100점): 거래대금(30) + 상승률(30) + 정배열(20) + 시총 통과(20)
7. 기술 분석 점수: 일목균형표 + `technical.analyze()` → `tech_score / engine_a_score / engine_b_score / tech_tags`
8. 상위 3개를 `sector_leaders` 테이블에 upsert 후 반환

**응답 예시**

```json
{
  "status": "success",
  "sector": "반도체(AI/HBM)",
  "updated_at": "2026-05-26T09:05:12.000Z",
  "data": [
    {
      "rank": 1,
      "stock_code": "000660",
      "stock_name": "SK하이닉스",
      "current_price": 198500,
      "change_rate": 3.12,
      "volume": 5820100,
      "market_cap": 1443000,
      "transaction_amount": 115490000000,
      "score": 80,
      "score_detail": { "amount": 30, "rate": 30, "ma_aligned": 20, "mktcap": 20 },
      "tags": ["거래대금", "상승률", "정배열"],
      "ma5": 195000,
      "ma20": 188000,
      "ma60": 175000,
      "ma_aligned": true,
      "tech_score": 72,
      "engine_a_score": 72,
      "engine_b_score": 0,
      "tech_tags": ["골든크로스", "강한 상승추세"]
    }
  ]
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `updated_at` | string \| null | 캐시 최종 갱신 시각 (캐시 없으면 null) |
| `data[].rank` | integer | 순위 (1–3) |
| `data[].stock_code` | string | 종목 코드 |
| `data[].stock_name` | string | 종목명 (`stock_master` DB 기준) |
| `data[].current_price` | number | 현재가 (원) |
| `data[].change_rate` | number | 등락률 (%) |
| `data[].market_cap` | number | 시가총액 (억원) |
| `data[].transaction_amount` | number | 누적 거래대금 (원) |
| `data[].score` | integer | 종합 점수 (0–100) |
| `data[].score_detail` | object | 항목별 점수 (amount / rate / ma_aligned / mktcap) |
| `data[].tags` | string[] | 강점 태그 (거래대금 / 상승률 / 정배열) |
| `data[].ma5` / `ma20` / `ma60` | number \| null | 이동평균 (DB OHLCV 130일 기준) |
| `data[].ma_aligned` | boolean | 정배열 여부 (5MA > 20MA > 60MA) |
| `data[].tech_score` | integer | 기술 분석 점수 (0–100, 오늘의 추천 알고리즘 동일) |
| `data[].engine_a_score` | integer | Engine A 추세 돌파형 점수 |
| `data[].engine_b_score` | integer | Engine B 역추세 반등형 점수 |
| `data[].tech_tags` | string[] | 기술 분석 태그 |

| 상태코드 | 의미 |
|----------|------|
| 200 | 정상 (캐시 없어도 200, `data: []`) |
| 400 | 지원하지 않는 섹터명 |
| 500 | KIS API 또는 DB 오류 |

---

### GET /api/v1/stocks/sector-leader/all

전체 20개 섹터의 캐시 데이터를 `sector_leaders` 테이블에서 단일 쿼리로 반환합니다. 프론트엔드 "전체" 탭에서 사용합니다.

**Query Parameters**: 없음

**응답 예시**

```json
{
  "status": "success",
  "data": [
    {
      "sector": "반도체(AI/HBM)",
      "leaders": [ { "rank": 1, "stock_code": "000660", ... } ],
      "updated_at": "2026-05-26T09:05:12.000Z"
    },
    {
      "sector": "온디바이스 AI",
      "leaders": [],
      "updated_at": null
    }
  ]
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `data[].sector` | string | 섹터명 |
| `data[].leaders` | array | 해당 섹터 주도주 배열 (캐시 없으면 `[]`) |
| `data[].updated_at` | string \| null | 캐시 최종 갱신 시각 |

| 상태코드 | 의미 |
|----------|------|
| 200 | 정상 |

---

### POST /api/v1/stocks/sector-leader/refresh

전체 20개 섹터를 KIS API에서 순차적으로 재조회하여 `sector_leaders` 테이블을 갱신합니다. 스케줄러(09:05 KST)가 자동 호출하며, 수동으로도 실행 가능합니다.

**Request Body**: 없음

**처리 로직**

- 20개 섹터를 순차 처리 (한 섹터씩 KIS API 호출 → DB upsert)
- 글로벌 세마포어(5) 적용으로 KIS API 과부하 방지
- 개별 섹터 실패 시 로그 기록 후 다음 섹터 계속 진행

**응답 예시**

```json
{ "status": "success", "message": "20개 섹터 갱신 완료" }
```

| 상태코드 | 의미 |
|----------|------|
| 200 | 정상 완료 |
| 500 | 전체 실패 |

---

### GET /api/v1/stocks/history

추천 종목 히스토리를 기간별로 조회합니다.

**Query Parameters**

| 파라미터 | 타입 | 필수 | 기본값 | 설명 |
|----------|------|------|--------|------|
| `type` | string | 아니오 | `daily` | `daily`(최근 7일) / `weekly`(최근 4주) / `monthly`(최근 6개월) |

**응답 예시**

```json
{
  "status": "success",
  "period_type": "daily",
  "data": [
    {
      "period_key": "2026-05-15",
      "period_type": "daily",
      "stocks": [
        {
          "stock_code": "005930",
          "stock_name": "삼성전자",
          "current_price": 74200,
          "change_rate": 2.35,
          "tags": ["A추세상승"],
          "tech_score": 82
        }
      ]
    }
  ]
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `data[].period_key` | string | `daily`: YYYY-MM-DD / `weekly`: YYYY-WNN / `monthly`: YYYY-MM |
| `data[].stocks` | array | 해당 기간 추천 종목 목록 |

| 상태코드 | 의미 |
|----------|------|
| 200 | 정상 |
| 500 | DB 조회 실패 |

---

### GET /api/v1/stocks/search

KOSPI·KOSDAQ 전체 종목(`stock_master` 테이블) 기반 종목명 검색. 대소문자 구분 없이 부분 일치 검색(ilike). 최대 50건 반환.

**Query Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| `q` | string | 예 | 검색할 종목명 (1자 이상) |

**응답 예시**

```json
{
  "status": "success",
  "data": [
    {
      "stock_code": "005930",
      "stock_name": "삼성전자",
      "market": "KOSPI"
    },
    {
      "stock_code": "009150",
      "stock_name": "삼성전기",
      "market": "KOSPI"
    }
  ]
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `data[].stock_code` | string | 종목 코드 (6자리) |
| `data[].stock_name` | string | 종목명 |
| `data[].market` | string | `"KOSPI"` 또는 `"KOSDAQ"` |

| 상태코드 | 의미 |
|----------|------|
| 200 | 정상 (결과 없어도 200, `data: []`) |

---

### GET /api/v1/stocks/{stock_code}/detail

특정 종목의 KIS API 실시간 데이터를 조회해 기술적 분석, 일목균형표, 기대 수익률 등을 포함해 반환합니다.

**Path Parameters**

| 파라미터 | 타입 | 예시 | 설명 |
|----------|------|------|------|
| `stock_code` | string | `005930` | 종목 코드 6자리 |

**응답 예시**

```json
{
  "status": "success",
  "data": {
    "stock_code": "005930",
    "stock_name": "삼성전자",
    "fetched_at": "2026-05-15 16:05:22",
    "current_price": 74200,
    "change_rate": 2.35,
    "change_amount": 1700,
    "volume": 14250300,
    "price_info": {
      "ref_price": 72500,
      "open": 72800,
      "high": 74500,
      "low": 72200,
      "upper_limit": 94200,
      "lower_limit": 50700,
      "w52_high": 88800,
      "w52_low": 52000,
      "market_cap": 4432000,
      "trade_amount": 1055940000000,
      "foreign_rate": 51.23,
      "eps": 4234,
      "bps": 50214
    },
    "metrics": {
      "per": 17.52,
      "pbr": 1.48,
      "roe": 8.35
    },
    "ichimoku": {
      "conversion_line": 73500,
      "base_line": 72400,
      "span_a": 72950,
      "span_b": 70800,
      "position": "above_cloud"
    },
    "technical": {
      "score": 82,
      "tags": ["A추세상승", "B모멘텀강세"],
      "signals": {
        "ma5": 73200,
        "ma20": 71500,
        "ma60": 69800,
        "macd": 420,
        "macd_signal": 310,
        "rsi": 58.3,
        "stoch_k": 72.1,
        "stoch_d": 65.4,
        "bb_upper": 76800,
        "bb_lower": 66200,
        "disparity": 103.8
      },
      "score_detail": {
        "A": 9,
        "B": 8,
        "C": 7,
        "D": 6
      },
      "strength": "강세"
    },
    "expected_return": {
      "dcf_target": 85000,
      "pbr_target": 74400,
      "upside_pct": 14.6,
      "stop_loss": 66200,
      "risk_reward": 2.4
    }
  }
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `price_info.ref_price` | integer \| null | 기준가 (전일 종가) |
| `price_info.market_cap` | integer \| null | 시가총액 (억원) |
| `price_info.foreign_rate` | number \| null | 외국인 보유율 (%) |
| `metrics.per` | number \| null | 주가수익비율 |
| `metrics.pbr` | number \| null | 주가순자산비율 |
| `metrics.roe` | number \| null | 자기자본이익률 |
| `ichimoku.position` | string | `"above_cloud"` / `"in_cloud"` / `"below_cloud"` / `"unknown"` |
| `technical.score` | integer | 0–100 기술적 분석 종합 점수 |
| `technical.score_detail` | object | 카테고리별 점수 (A: 추세, B: 모멘텀, C: 변동성, D: 거래량 — 각 0–10) |
| `technical.strength` | string | `"강세"` / `"중립"` / `"약세"` |
| `expected_return.dcf_target` | number \| null | DCF 목표주가 |
| `expected_return.pbr_target` | number \| null | PBR 목표주가 |
| `expected_return.upside_pct` | number \| null | 상승 여력 (%) |
| `expected_return.stop_loss` | number \| null | 기술적 손절가 (볼린저 하단) |
| `expected_return.risk_reward` | number \| null | 리스크/리워드 비율 |

**비고**

- 일목균형표는 KIS API에서 130일 OHLCV를 실시간 조회하여 계산. 52봉 미만이면 모두 `0` / `"unknown"` 반환.
- `tech_score` 계산: 4개 카테고리(A추세·B모멘텀·C변동성·D거래량) × 최대 10점 = 40점 → ×2.5 → 0–100 환산.
- `stock_name`은 `stock_recommendations` 캐시 → 히스토리 → 코드 순으로 조회합니다.

| 상태코드 | 의미 |
|----------|------|
| 200 | 정상 |
| 500 | KIS API 호출 실패 또는 파싱 오류 |

---

### POST /api/v1/stocks/sync/recommendations

KIS API를 즉시 호출해 추천 종목을 업데이트하고 `stock_recommendations` 테이블에 저장합니다. 히스토리 스냅샷(`recommendation_history`)도 함께 저장합니다.

**Request Body**: 없음

**처리 로직**

1. KIS `get_volume_ranking()` API 호출 → 거래량 순위 종목 조회 (실서버 전용)
2. ETF/ETN 자동 제외 (종목 코드 영문자 포함 / KODEX·TIGER 등 키워드)
3. 상위 30개 종목의 130일 OHLCV 병렬 수집 (`asyncio.Semaphore=5`)
4. `technical.analyze(records)` — 4카테고리 기술 지표 스코어 계산 (0–100)
5. 기술 스코어 내림차순 → 상위 10개 선택
6. 보조 태그 추가: 등락률 ≥ 3% → `"등락률 급등"`, 현재가 ≥ 52주 신고가 × 95% → `"52주 신고가 근접"`
7. KIS API 실패 시 → FALLBACK_STOCKS 사용 (tags: `["폴백 데이터"]`)
8. 오늘 날짜 기존 레코드 삭제 후 신규 삽입 + 히스토리 스냅샷 저장

**응답 예시**

```json
{
  "status": "success",
  "count": 10,
  "data": [
    {
      "date": "2026-05-15",
      "stock_code": "035420",
      "stock_name": "NAVER",
      "current_price": 192000,
      "change_rate": 3.76,
      "volume": 8320100,
      "tech_score": 87,
      "tags": ["A추세상승", "B모멘텀강세", "등락률 급등"]
    }
  ]
}
```

| 상태코드 | 의미 |
|----------|------|
| 200 | 정상 (폴백 포함) |
| 500 | 내부 오류 (DB 저장 실패 등) |

---

### POST /api/v1/stocks/sync/ohlcv

지정한 종목 코드의 일별 OHLCV 데이터를 KIS API에서 조회해 `stock_ohlcv` 테이블에 upsert합니다.

**Request Body** (application/json, 선택)

```json
{
  "stock_codes": ["005930", "000660", "035420"]
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `stock_codes` | string[] \| null | 아니오 | 미제공 시 거래량 순위 상위 50개 종목 자동 조회 |

**응답 예시**

```json
{
  "status": "success",
  "synced_stocks": 3,
  "total_rows": 1482,
  "errors": []
}
```

| 상태코드 | 의미 |
|----------|------|
| 200 | 정상 완료 (일부 오류 있어도 200) |
| 500 | 전체 실패 |

---

### POST /api/v1/stocks/sync/master

KRX(`kind.krx.co.kr`)에서 KOSPI·KOSDAQ 전체 종목 목록을 다운로드하여 `stock_master` 테이블에 upsert합니다.

**Request Body**: 없음

**응답 예시**

```json
{
  "status": "success",
  "total": 2657
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `total` | integer | upsert된 총 종목 수 (KOSPI + KOSDAQ) |

**비고**

- KRX HTML은 EUC-KR 인코딩으로 제공되며, HTMLParser로 파싱합니다.
- 500건 단위 batch upsert.
- 정기 실행 없음 — 필요 시 수동 호출.

| 상태코드 | 의미 |
|----------|------|
| 200 | 정상 |
| 500 | KRX 다운로드 또는 DB upsert 실패 |

---

## 보유 종목 (Holdings)

### GET /api/v1/holdings

보유 종목 목록과 손익 요약을 반환합니다. 현재가는 `stock_recommendations` 캐시 우선, 없으면 KIS API에서 직접 조회합니다.

**Query Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| `profile_id` | integer | 아니오 | 지정 시 해당 프로필의 보유 종목만 반환 |

**응답 예시**

```json
{
  "status": "success",
  "data": [
    {
      "id": 1,
      "stock_code": "005930",
      "stock_name": "삼성전자",
      "avg_price": 68000,
      "quantity": 10,
      "memo": "장기보유",
      "profile_id": 1,
      "created_at": "2026-04-01T10:00:00.000Z",
      "updated_at": "2026-05-01T10:00:00.000Z",
      "current_price": 74200,
      "change_rate": 2.35,
      "purchase_amount": 680000,
      "eval_amount": 742000,
      "profit_loss": 62000,
      "profit_rate": 9.12
    }
  ],
  "summary": {
    "total_purchase": 680000,
    "total_eval": 742000,
    "total_profit_loss": 62000,
    "total_profit_rate": 9.12
  }
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `data[].avg_price` | integer | 평균 매수 단가 (원) |
| `data[].quantity` | integer | 보유 수량 |
| `data[].current_price` | integer \| null | 현재가 (조회 실패 시 null) |
| `data[].change_rate` | number \| null | 당일 등락률 (%) |
| `data[].purchase_amount` | integer | 매수 금액 = 평균단가 × 수량 |
| `data[].eval_amount` | integer \| null | 평가 금액 = 현재가 × 수량 |
| `data[].profit_loss` | integer \| null | 평가 손익 (원) |
| `data[].profit_rate` | number \| null | 수익률 (%) |
| `summary.total_purchase` | integer | 전체 매수 금액 합계 |
| `summary.total_eval` | integer \| null | 현재가 있는 종목의 평가 금액 합계 |
| `summary.total_profit_rate` | number \| null | 전체 수익률 (%) |

| 상태코드 | 의미 |
|----------|------|
| 200 | 정상 |
| 500 | DB 조회 실패 |

---

### POST /api/v1/holdings

보유 종목을 추가합니다.

**Request Body** (application/json)

```json
{
  "stock_code": "005930",
  "stock_name": "삼성전자",
  "avg_price": 68000,
  "quantity": 10,
  "memo": "장기보유",
  "profile_id": 1
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `stock_code` | string | 예 | 종목 코드 |
| `stock_name` | string | 예 | 종목명 |
| `avg_price` | integer | 예 | 평균 매수 단가 (원) |
| `quantity` | integer | 예 | 보유 수량 |
| `memo` | string | 아니오 | 메모 |
| `profile_id` | integer | 아니오 | 프로필 ID (미제공 시 미분류) |

**응답 예시**

```json
{
  "status": "success",
  "data": {
    "id": 1,
    "stock_code": "005930",
    "stock_name": "삼성전자",
    "avg_price": 68000,
    "quantity": 10,
    "memo": "장기보유",
    "profile_id": 1,
    "created_at": "2026-05-15T10:00:00.000Z"
  }
}
```

| 상태코드 | 의미 |
|----------|------|
| 200 | 정상 생성 |
| 400 | 종목 코드 미입력 |
| 500 | DB 저장 실패 |

---

### PUT /api/v1/holdings/{holding_id}

보유 종목 정보를 수정합니다. 제공된 필드만 업데이트합니다.

**Path Parameters**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `holding_id` | integer | 보유 종목 ID |

**Request Body** (application/json)

```json
{
  "avg_price": 70000,
  "quantity": 15,
  "memo": "추가 매수",
  "profile_id": null
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `avg_price` | integer | 아니오 | 새 평균 단가 |
| `quantity` | integer | 아니오 | 새 수량 |
| `memo` | string | 아니오 | 메모 |
| `profile_id` | integer \| null | 아니오 | 프로필 재배정. `null` 명시 시 프로필 해제 |

**비고**: `profile_id`는 필드가 요청에 포함된 경우에만 업데이트됩니다 (`null` 포함).

| 상태코드 | 의미 |
|----------|------|
| 200 | 정상 수정 |
| 400 | 변경할 항목 없음 |
| 500 | DB 실패 |

---

### DELETE /api/v1/holdings/{holding_id}

보유 종목을 삭제합니다.

**Path Parameters**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `holding_id` | integer | 보유 종목 ID |

**응답 예시**

```json
{ "status": "success" }
```

| 상태코드 | 의미 |
|----------|------|
| 200 | 정상 삭제 |
| 500 | DB 실패 |

---

### GET /api/v1/holdings/{holding_id}/sell-analysis

보유 종목의 매도 신호를 기술적·기본적·자산관리 관점으로 통합 분석합니다.

**Path Parameters**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `holding_id` | integer | 보유 종목 ID |

**처리 로직**

1. 보유 종목 조회 (avg_price, quantity)
2. KIS API — 현재가 + 130일 OHLCV 병렬 조회
3. 포트폴리오 전체 평가금액 대비 해당 종목 비중 계산
4. `analyze_sell()` — 기술적(이동평균 데드크로스, RSI 과매수, 볼린저 이탈 등) + 기본적(PER 과열, PBR 고평가) + 자산관리(비중 과집중, 수익률 목표 달성) 분석

**응답 예시**

```json
{
  "status": "success",
  "data": {
    "score": 65,
    "signals": ["RSI 과매수", "PBR 고평가", "비중 과집중"],
    "recommendation": "부분 매도 검토",
    "detail": {
      "technical_score": 25,
      "fundamental_score": 20,
      "risk_score": 20
    },
    "portfolio_weight": 35.2,
    "current_price": 74200
  }
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `data.score` | integer | 매도 신호 종합 점수 (0–100, 높을수록 매도 신호 강함) |
| `data.signals` | string[] | 감지된 매도 신호 목록 |
| `data.recommendation` | string | 매도 권고 문구 |
| `data.portfolio_weight` | number \| null | 포트폴리오 내 비중 (%) |
| `data.current_price` | integer \| null | 현재가 |

| 상태코드 | 의미 |
|----------|------|
| 200 | 정상 |
| 404 | 보유 종목 없음 |
| 500 | KIS API 또는 분석 실패 |

---

## 투자 프로필 (Profiles)

### GET /api/v1/profiles

등록된 투자 프로필 목록을 반환합니다.

**응답 예시**

```json
{
  "status": "success",
  "data": [
    {
      "id": 1,
      "name": "성장주 포트폴리오",
      "analysis_type": "quant",
      "created_at": "2026-04-01T10:00:00.000Z"
    },
    {
      "id": 2,
      "name": "배당주 포트폴리오",
      "analysis_type": "dividend",
      "created_at": "2026-04-10T10:00:00.000Z"
    }
  ]
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `data[].name` | string | 프로필 이름 |
| `data[].analysis_type` | string | `"quant"` (퀀트) 또는 `"dividend"` (배당) |

| 상태코드 | 의미 |
|----------|------|
| 200 | 정상 |
| 500 | DB 조회 실패 |

---

### POST /api/v1/profiles

투자 프로필을 생성합니다.

**Request Body** (application/json)

```json
{
  "name": "성장주 포트폴리오",
  "analysis_type": "quant"
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `name` | string | 예 | 프로필 이름 |
| `analysis_type` | string | 아니오 | `"quant"` (기본값) 또는 `"dividend"` |

| 상태코드 | 의미 |
|----------|------|
| 200 | 정상 생성 |
| 400 | 이름 미입력 |
| 500 | DB 실패 |

---

### PUT /api/v1/profiles/{profile_id}

프로필 정보를 수정합니다.

**Path Parameters**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `profile_id` | integer | 프로필 ID |

**Request Body** (application/json)

```json
{
  "name": "새 이름",
  "analysis_type": "dividend"
}
```

| 상태코드 | 의미 |
|----------|------|
| 200 | 정상 수정 |
| 400 | 이름 비어 있음 / 잘못된 `analysis_type` / 변경 항목 없음 |
| 500 | DB 실패 |

---

### DELETE /api/v1/profiles/{profile_id}

프로필을 삭제합니다.

**비고**: 연결된 `holdings.profile_id`는 `NULL`로 처리됩니다 (DB ON DELETE SET NULL).

**응답 예시**

```json
{ "status": "success" }
```

| 상태코드 | 의미 |
|----------|------|
| 200 | 정상 삭제 |
| 500 | DB 실패 |

---

## 포트폴리오 분석 (Portfolio)

### GET /api/v1/portfolio/analysis

캐시된 AI 포트폴리오 분석 결과를 반환합니다. `holdings_hash`를 전달하면 캐시 유효 여부(`is_stale`)도 함께 반환합니다.

**Query Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| `profile_id` | integer | 아니오 | 특정 프로필 분석 조회 |
| `holdings_hash` | string | 아니오 | 클라이언트 측 현재 보유 해시. 제공 시 `is_stale` 비교에 사용 |

**응답 예시 (캐시 있음)**

```json
{
  "status": "success",
  "data": {
    "analysis_text": "## 포트폴리오 진단 리포트\n...",
    "updated_at": "2026-05-15T16:30:00.000Z"
  },
  "is_stale": false
}
```

**응답 예시 (캐시 없음)**

```json
{
  "status": "success",
  "data": null,
  "is_stale": true
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `data.analysis_text` | string \| null | Gemini 생성 분석 리포트 (Markdown) |
| `data.updated_at` | string \| null | 마지막 분석 생성 시각 |
| `is_stale` | boolean | `true`: 재분석 필요 |

| 상태코드 | 의미 |
|----------|------|
| 200 | 정상 |

---

### POST /api/v1/portfolio/analysis

보유 종목을 조회하여 Gemini AI로 포트폴리오 분석을 실행하고 결과를 저장합니다. 오늘 날짜에 동일한 보유 구성(holdings_hash)이면 캐시를 재사용합니다.

**Request Body** (application/json)

```json
{
  "profile_id": 1
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `profile_id` | integer | 아니오 | 분석할 프로필 ID. 미제공 시 전체 보유 종목 분석 |

**처리 로직**

1. 보유 종목 조회 + 현재가 enrichment
2. `compute_holdings_hash()` → 보유 구성 MD5 해시 (16자) 계산
3. 오늘 날짜 + 동일 해시 캐시 존재 시 캐시 반환 (Gemini 호출 없음)
4. 프로필의 `analysis_type` 확인 (`quant` 또는 `dividend`)
5. Gemini 2.5 Flash Lite (`gemini-2.5-flash-lite`)로 포트폴리오 분석 실행
6. 결과를 `portfolio_analyses` 테이블에 upsert 후 반환

**분석 내용 (Markdown 리포트)**

- 자산 배분 및 집중도 분석
- 기술적 모멘텀 분석
- 리스크 진단
- 종목별 투자 판단: 확대 권고 / 유지 / 축소·매도 + 신규 편입 추천 (1–3개)
- 액션 플랜

**응답 예시**

```json
{
  "status": "success",
  "data": {
    "analysis_text": "## 포트폴리오 진단 리포트\n...",
    "updated_at": null
  },
  "is_stale": false
}
```

**비고**

- `updated_at`은 새로 생성 시 `null` 반환 (DB 저장 후 별도 조회 없이 응답).
- Gemini 호출 시간 약 10–30초 소요. 클라이언트에서 타임아웃 고려 필요.

| 상태코드 | 의미 |
|----------|------|
| 200 | 정상 (캐시 재사용 포함) |
| 400 | 분석할 보유 종목 없음 |
| 500 | Gemini API 실패 |

---

> **리포트 API** (`/api/v1/reports/*`)는 ARA 프로젝트(http://localhost:8001)로 분리되었습니다.

---

## 가상 거래 (Virtual)

### GET /api/v1/virtual/accounts

가상 거래 계좌 목록을 반환합니다.

**Query Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| `profile_id` | integer | 아니오 | 지정 시 해당 프로필의 계좌만 반환 |

**응답 예시**

```json
{
  "status": "success",
  "data": [
    {
      "id": 1,
      "profile_id": 1,
      "name": "성장형 계좌",
      "initial_cash": 10000000,
      "current_cash": 8420000,
      "strategy": "both",
      "min_score": 50,
      "max_positions": 5,
      "position_size": 20,
      "stop_loss_pct": 10,
      "take_profit_pct": 20,
      "is_active": true,
      "created_at": "2026-05-20T10:00:00.000Z"
    }
  ]
}
```

---

### POST /api/v1/virtual/accounts

가상 거래 계좌를 생성합니다.

**Request Body** (application/json)

```json
{
  "name": "성장형 계좌",
  "profile_id": 1,
  "initial_cash": 10000000,
  "strategy": "both",
  "min_score": 50,
  "max_score": null,
  "score_filter_type": "gte",
  "max_positions": 5,
  "position_size": 20,
  "stop_loss_pct": 10,
  "take_profit_pct": 20,
  "max_hold_days": null,
  "filter_excl_large_cap": false,
  "filter_large_cap_threshold": null,
  "filter_excl_high_amount": false,
  "filter_high_amount_threshold": null
}
```

| 필드 | 타입 | 필수 | 기본값 | 설명 |
|------|------|------|--------|------|
| `name` | string | 예 | — | 계좌명 |
| `profile_id` | integer | 아니오 | — | 연결 프로필 |
| `initial_cash` | integer | 아니오 | 10000000 | 초기 자금 (원) |
| `strategy` | string | 아니오 | `"both"` | `engine_a` / `engine_b` / `both` (A 또는 B) / `both_and` (A 및 B 동시 충족) |
| `min_score` | integer | 아니오 | 50 | 매수 최소 기술 점수 |
| `max_score` | integer \| null | 아니오 | null | 매수 최대 점수 (`lte`/`range` 전략 시 상한) |
| `score_filter_type` | string | 아니오 | `"gte"` | 점수 필터 유형: `gte` (min 이상) / `lte` (max 이하) / `range` (min~max) |
| `max_positions` | integer | 아니오 | 5 | 최대 보유 종목 수 |
| `position_size` | integer | 아니오 | 20 | 종목당 투자 비율 (%) |
| `stop_loss_pct` | integer | 아니오 | 10 | 손절 기준 (%) |
| `take_profit_pct` | integer | 아니오 | 20 | 익절 기준 (%) |
| `max_hold_days` | integer \| null | 아니오 | null | 최대 보유 일수 (초과 시 `max_hold_exit` 강제 청산) |
| `filter_excl_large_cap` | boolean | 아니오 | false | 대형주 제외 여부 (Engine B 리스크 관리) |
| `filter_large_cap_threshold` | integer \| null | 아니오 | null | 대형주 시가총액 임계값 (억원, `filter_excl_large_cap=true` 시 유효) |
| `filter_excl_high_amount` | boolean | 아니오 | false | 고유동성 종목 제외 여부 |
| `filter_high_amount_threshold` | integer \| null | 아니오 | null | 거래대금 임계값 (억원, `filter_excl_high_amount=true` 시 유효) |

| 상태코드 | 의미 |
|----------|------|
| 200 | 정상 생성 |
| 500 | DB 저장 실패 |

---

### PATCH /api/v1/virtual/accounts/{account_id}

가상 계좌 설정을 수정합니다. 제공된 필드만 업데이트합니다 (초기자금 `initial_cash` 변경 불가).

**Path Parameters**

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `account_id` | integer | 계좌 ID |

**Request Body** (application/json, 모든 필드 선택)

```json
{
  "name": "수정된 계좌명",
  "strategy": "engine_a",
  "score_filter_type": "range",
  "min_score": 50,
  "max_score": 80,
  "max_positions": 5,
  "position_size": 20,
  "stop_loss_pct": 10,
  "take_profit_pct": 20,
  "max_hold_days": null,
  "filter_excl_large_cap": false,
  "filter_large_cap_threshold": null,
  "filter_excl_high_amount": false,
  "filter_high_amount_threshold": null
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `name` | string | 계좌명 |
| `strategy` | string | `engine_a` / `engine_b` / `both` / `both_and` |
| `score_filter_type` | string | `gte` / `lte` / `range` |
| `min_score` | integer | 매수 최소 기술 점수 |
| `max_score` | integer \| null | 매수 최대 점수 (`lte`/`range` 시 유효) |
| `max_positions` | integer | 최대 보유 종목 수 |
| `position_size` | integer | 종목당 투자 비율 (%) |
| `stop_loss_pct` | integer | 손절 기준 (%) |
| `take_profit_pct` | integer | 익절 기준 (%) |
| `max_hold_days` | integer \| null | 최대 보유 일수 (null = 제한 없음) |
| `filter_excl_large_cap` | boolean | 대형주 제외 여부 |
| `filter_large_cap_threshold` | integer \| null | 대형주 시총 임계값 (억원) |
| `filter_excl_high_amount` | boolean | 고유동성 종목 제외 여부 |
| `filter_high_amount_threshold` | integer \| null | 거래대금 임계값 (억원) |

**응답 예시**

```json
{ "status": "success", "data": { "id": 1, "name": "수정된 계좌명", ... } }
```

| 상태코드 | 의미 |
|----------|------|
| 200 | 정상 수정 |
| 404 | 계좌 없음 |
| 500 | DB 실패 |

---

### DELETE /api/v1/virtual/accounts/{account_id}

가상 계좌를 삭제합니다. 연결된 포지션·체결 내역도 CASCADE 삭제됩니다.

---

### GET /api/v1/virtual/accounts/{account_id}/positions

계좌의 보유 포지션 목록을 반환합니다. KIS API에서 현재가를 조회하여 평가손익을 계산합니다.

**응답 예시**

```json
{
  "status": "success",
  "data": [
    {
      "id": 1,
      "stock_code": "005930",
      "stock_name": "삼성전자",
      "quantity": 30,
      "avg_price": 68600,
      "entry_date": "2026-05-20",
      "entry_score": 82,
      "engine": "A",
      "entry_atr": 1850,
      "highest_price": 76000,
      "half_exited": false,
      "entry_low": 67400,
      "current_price": 74200,
      "profit_loss": 168000,
      "profit_rate": 8.16
    }
  ]
}
```

---

### GET /api/v1/virtual/accounts/{account_id}/trades

계좌의 체결 내역을 반환합니다.

**Query Parameters**

| 파라미터 | 타입 | 필수 | 기본값 | 설명 |
|----------|------|------|--------|------|
| `limit` | integer | 아니오 | 100 | 최대 반환 건수 (max 500) |

**응답 예시**

```json
{
  "status": "success",
  "data": [
    {
      "id": 5,
      "stock_code": "005930",
      "stock_name": "삼성전자",
      "side": "sell",
      "quantity": 30,
      "price": 78000,
      "amount": 2340000,
      "trigger_type": "take_profit",
      "engine": "A",
      "tech_score": 82,
      "sell_score": null,
      "pnl": 282000,
      "pnl_rate": 13.74,
      "traded_at": "2026-05-28"
    }
  ]
}
```

| 필드 | 설명 |
|------|------|
| `trigger_type` | 매수: `algo_buy` / `manual` · 매도(공통): `stop_loss` / `take_profit` / `max_hold_exit` · 매도(A): `atr_hard_stop` / `atr_trailing_stop` / `rsi_exhaustion` · 매도(B): `entry_low_breach` / `time_limit_stop` / `ma20_half_exit` / `target_reached` |
| `pnl` | 실현손익 (매도 시). 매수 시 `null` |
| `pnl_rate` | 수익률 (%). 매도 시만 |

---

### GET /api/v1/virtual/accounts/{account_id}/performance

계좌 성과 요약을 반환합니다.

**응답 예시**

```json
{
  "status": "success",
  "data": {
    "initial_cash": 10000000,
    "current_cash": 8420000,
    "position_value": 1780000,
    "total_value": 10200000,
    "total_return_rate": 2.0,
    "realized_pnl": 450000,
    "unrealized_pnl": 168000,
    "win_rate": 66.7,
    "trade_count": 6,
    "sell_count": 3,
    "avg_hold_days": 4.5,
    "max_drawdown": -8.2
  }
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `initial_cash` | integer | 초기 자금 (원) |
| `current_cash` | integer | 잔여 현금 (원) |
| `position_value` | integer | 보유 포지션 평가금액 합계 |
| `total_value` | integer | 총 평가금액 (현금 + 포지션) |
| `total_return_rate` | number | 초기 자금 대비 수익률 (%) |
| `realized_pnl` | integer | 실현 손익 합계 (원) |
| `unrealized_pnl` | integer | 미실현 손익 합계 (원) |
| `win_rate` | number \| null | 승률 (매도 건 중 PnL>0 비율, %) |
| `trade_count` | integer | 총 거래 건수 (매수+매도) |
| `sell_count` | integer | 매도 체결 건수 |
| `avg_hold_days` | number \| null | 평균 보유 일수 |
| `max_drawdown` | number \| null | 최대 손실률 (%, 매도 체결 기준 근사값) |

---

### POST /api/v1/virtual/accounts/{account_id}/trades

수동 매매를 체결합니다.

**Request Body** (application/json)

```json
{
  "stock_code": "005930",
  "stock_name": "삼성전자",
  "side": "buy",
  "quantity": 10,
  "price": 74200,
  "memo": "수동 매수"
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `stock_code` | string | 예 | 종목 코드 |
| `stock_name` | string | 예 | 종목명 |
| `side` | string | 예 | `"buy"` 또는 `"sell"` |
| `quantity` | integer | 예 | 수량 |
| `price` | integer | 예 | 체결가 |
| `memo` | string | 아니오 | 메모 |

| 상태코드 | 의미 |
|----------|------|
| 200 | 정상 체결 |
| 400 | 잔고 부족 / 매도 수량 초과 |
| 404 | 계좌 없음 |
| 500 | DB 실패 |

---

## 내부 서비스 구조 참고

### 기술적 분석 엔진 (`services/technical.py`)

`analyze(records, cloud_position, market_regime) → {"score": int, "engine": str, "engine_a_score": int, "engine_b_score": int, "tags": list, "signals": dict, "strength": str}`

**듀얼 엔진 구조**: `score = max(engine_a_score, engine_b_score)`. 이기는 엔진의 tags 채택.

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `records` | list[dict] | OHLCV (stck_clpr/hgpr/lwpr/acml_vol), 오름차순 |
| `cloud_position` | str | `"above_cloud"` / `"in_cloud"` / `"below_cloud"` / `"unknown"` |
| `market_regime` | str | `"BULL"` / `"BEAR"` — KOSPI MA20 기반, 기본값 `"BULL"` |

**Stage 1 — Hard Filter**: MA20 거래량 < 100,000주 → score=0 즉시 탈락.

**Engine A — 추세 돌파형 (max 100pt)**

BEAR 시장(`market_regime="BEAR"`) 즉시 0점.

| 항목 | 배점 |
|------|------|
| 골든크로스 (MA5>MA20>MA60 정배열 → 15 / MA5>MA20 → 8) | max 15 |
| ADX/DMI 강한 상승추세 (ADX≥25 → 15 / ≥20 → 10) | max 15 |
| 일목 구름대 돌파 (above_cloud → 15 / in_cloud → 5) | max 15 |
| 볼린저 스퀴즈 상단돌파 (밴드폭<10%+상단 → 15 / 중간> → 6) | max 15 |
| 전고점 돌파 (21일 고점+거래량≥1.5× → 15 / 미충족 → 8) | max 15 |
| OBV 선행 돌파 (OBV>고점+주가≤고점 → 15 / OBV>고점만 → 8) | max 15 |
| 거래량 급증 (≥3.0×+양봉 → 10 / ≥2.0× → 7 / ≥1.5× → 3) | max 10 |
| RSI Hard Veto: ≥80 → **즉시 0점** | — |
| RSI 최초 70 돌파(직전<70): +5 | — |
| RSI 지속 70+: max(0, score−10) | — |

**Engine B — 역추세 반등형 (max 100pt)**

Pre-filter: 거래대금<50억 또는 MA60 우하향 → 즉시 0점.

**B1 (disparity < 99)**: (이격도 + 과매도 + 수요밴드) / 75 × 100

**B2 (disparity ≥ 99)**: (과매도 + 수요밴드 + 눌림목) / 85 × 100

| 항목 | B1 | B2 | 배점 |
|------|:---:|:---:|------|
| 이격도 저점 (<93%→15 / <95%→12 / <97%→8 / <99%→3) | ✓ | — | max 15 |
| 과매도 그룹 RSI/Stoch/CCI/MFI (≥3→25 / ≥2→20 / 1→10) | ✓ | ✓ | max 25 |
| 수요밴드 통합 볼린저·엔벨로프·피봇S2·피보나치 (≥2+양봉→35 …) | ✓ | ✓ | max 35 |
| 눌림목 반등 (MA5>MA20+MA20터치+양봉→25 / 미충족→12) | — | ✓ | max 25 |

`strength` 값: `"매우 강함"` (≥75) / `"강함"` (≥50) / `"보통"` (≥25) / `"약함"` (<25)

---

### 매도 신호 분석 (`services/sell_signal.py`)

`analyze_sell(records, avg_price, current_price, per, pbr, eps, w52_high, portfolio_weight, engine, entry_atr, highest_price, holding_bars, half_exited, entry_low)`

5개 관점 통합 분석:
- **기술적**: 데드크로스, RSI 과매수(>70), 볼린저 상단 이탈, MACD 하향 교차
- **엔진A**: ATR 하드 스탑(진입가−1.5×ATR), ATR 트레일링 스탑(최고가−2.0×ATR), RSI 모멘텀 소멸(70→이하 하향)
- **엔진B**: 보유 기간 손절(5봉+손실), MA20 최초 터치 분할 익절, 이격도≥102%/RSI≥60 목표 도달, 진입 저점 이탈
- **기본적**: PER/PBR 과열
- **자산관리**: 단일 종목 비중 초과, 손절(-5%/-10%), 트레일링 스탑(-7%)

---

### KIS API 클라이언트 (`services/kis_api.py`)

FastAPI 시작 시 싱글턴 `kis_client` 인스턴스 생성. 첫 API 호출 시 OAuth2 토큰 자동 발급 후 파일 캐시(`.kis_token_cache.json`) 및 메모리 캐시에 저장. 만료 300초 전 자동 재발급.

| 메서드 | KIS TR ID | 설명 |
|--------|-----------|------|
| `get_stock_price(stock_code)` | `FHKST01010100` | 현재가·PER·PBR·EPS·BPS·ROE 조회 |
| `get_daily_ohlcv(stock_code, start, end)` | `FHKST03010100` | 일별 OHLCV 차트 조회 |
| `get_volume_ranking()` | `FHPST01700000` | 거래량 순위 조회 (실서버 전용) |
| `get_trading_amount_ranking()` | `FHPST01700000` | 거래대금 순위 조회 |
| `get_foreign_net_buy_ranking()` | `FHPTJ04400000` | 외국인 순매수 상위 종목 (`fid_etc_cls_code=1`) |
| `get_institution_net_buy_ranking()` | `FHPTJ04400000` | 기관 순매수 상위 종목 (`fid_etc_cls_code=2`) |
| `get_institution_foreign_net_buy_ranking()` | `FHPTJ04400000` | 기관·외국인 합산 순매수 (수급 현황용, `fid_etc_cls_code=0`) |
| `get_52week_high_low(div_cls)` | `FHPST01870000` | 52주 신고가(`"1"`) 또는 신저가(`"2"`) 종목 |
| `get_index_chart(market, start, end, period)` | `FHKUP03500100` | 지수 차트 (output1: 현재값, output2: 차트 시계열) |

---

### 스케줄러 (`services/scheduler.py`)

- 엔진: APScheduler `AsyncIOScheduler` (Asia/Seoul 타임존)
- 시작 체크: 서버 기동 시 당일 추천 종목 없으면 즉시 업데이트
- 실행 일정 (평일):
  - **08:50 KST**: 전일 마감 데이터 기반 추천 종목 갱신 + 가상 거래 트리거 + 텔레그램 리포트
  - **09:05 KST**: 섹터 주도주 전체 20개 갱신
  - **11:00 KST**: 오전 장중 추천 종목 갱신 + 가상 거래 트리거 + 텔레그램 리포트
  - **14:00 KST**: 오후 장중 추천 종목 갱신 + 가상 거래 트리거 + 텔레그램 리포트
  - **16:10 KST**: 당일 장마감 후 추천 종목 업데이트 + OHLCV 동기화 + 히스토리 저장 + 가상 거래 트리거 + 텔레그램 리포트
- **가상 거래 트리거 가격 소스**: `_fetch_realtime_prices()` — 포지션 보유 종목 전체를 KIS `get_stock_price()`로 병렬 조회(세마포어 5) → 실시간가 `price_map`을 매도·매수 트리거에 전달 (조건 검색 스냅샷 가격 미사용)
- 각 동기화 완료 후 `ENABLE_TELEGRAM=true` 시 텔레그램 추천 리포트 전송 (로컬 전용)
- 가상 체결 시 `ENABLE_TELEGRAM=true` 시 매수·매도 알림 즉시 전송

---

### Gemini AI 연동 (`services/gemini.py`)

- 모델: `gemini-2.5-flash-lite`
- 포트폴리오 분석: 보유 종목 데이터 → Markdown 리포트 생성 (퀀트/배당 프롬프트 분기)

---

### 종목 마스터 동기화 (`services/stock_master_sync.py`)

- 소스: `kind.krx.co.kr` HTML 다운로드 (EUC-KR 인코딩)
- KOSPI(`stockMkt`) + KOSDAQ(`kosdaqMkt`) 각각 요청
- HTMLParser로 테이블 파싱 → `stock_master` 테이블 500건 단위 upsert

---

## 시장 현황 (Market)

### GET /api/v1/market/indices

8개 주요 시장 지표를 반환합니다. in-memory 1분 캐시.

**응답 예시**

```json
{
  "status": "success",
  "data": {
    "kospi":     { "label": "KOSPI",      "price": 2850.12, "change": 12.34, "change_rate": 0.44, "sign": "2" },
    "kosdaq":    { "label": "KOSDAQ",     "price": 840.55,  "change": -2.10, "change_rate": -0.25, "sign": "4" },
    "nasdaq":    { "label": "NASDAQ",     "price": 19234.56,"change": 88.40, "change_rate": 0.46, "sign": "2" },
    "dow":       { "label": "다우존스",   "price": 42100.00,"change": -30.0, "change_rate": -0.07, "sign": "4" },
    "sp500":     { "label": "S&P 500",    "price": 5820.10, "change": 15.20, "change_rate": 0.26, "sign": "2" },
    "usd_krw":   { "label": "USD/KRW",   "price": 1380.50, "change": 2.30,  "change_rate": 0.17, "sign": "2" },
    "crude_oil": { "label": "WTI 유가",  "price": 78.45,   "change": -0.62, "change_rate": -0.78, "sign": "4" },
    "us10y":     { "label": "미국 10년물","price": 4.32,    "change": 0.05,  "change_rate": 1.17, "sign": "2" }
  }
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `*.label` | string | 지수 표시명 |
| `*.price` | number \| null | 현재 값 (조회 실패 시 null) |
| `*.change` | number \| null | 전일 대비 변동 |
| `*.change_rate` | number \| null | 전일 대비 등락률 (%) |
| `*.sign` | string | `"1"/"2"` 상승, `"3"` 보합, `"4"/"5"` 하락 |

**데이터 소스**

| 지수 | 소스 | 심볼 |
|------|------|------|
| KOSPI, KOSDAQ | KIS API `FHKUP03500100` output1 | `0001`, `1001` |
| NASDAQ, 다우존스, S&P 500 | Yahoo Finance | `^IXIC`, `^DJI`, `^GSPC` |
| USD/KRW, WTI 유가, 미국 10년물 | Yahoo Finance | `KRW=X`, `CL=F`, `^TNX` |

| 상태코드 | 의미 |
|----------|------|
| 200 | 정상 (일부 지수 조회 실패 시에도 200, 해당 필드 null) |

---

### GET /api/v1/market/rankings

주도주 8개 카테고리의 상위 N개 종목을 반환합니다. in-memory 2분 캐시.

**Query Parameters**

| 파라미터 | 타입 | 기본값 | 최대 | 설명 |
|----------|------|--------|------|------|
| `limit` | integer | 5 | 20 | 카테고리별 반환 종목 수 |

**응답 예시**

```json
{
  "status": "success",
  "data": {
    "rise": [
      { "stock_code": "012450", "stock_name": "한화에어로스페이스", "current_price": 1041000, "change_rate": 8.2, "volume": 382000, "amount": 398000000000 }
    ],
    "fall": [ ... ],
    "volume": [ ... ],
    "amount": [ ... ],
    "foreign_buy": [
      { "stock_code": "005930", "stock_name": "삼성전자", "current_price": 75000, "change_rate": 1.1, "net_buy": 1520000 }
    ],
    "institution_buy": [ ... ],
    "high_52w": [
      { "stock_code": "012450", "stock_name": "한화에어로스페이스", "current_price": 1041000, "change_rate": 8.2, "high_52w": 1050000, "low_52w": 420000 }
    ],
    "low_52w": [ ... ]
  }
}
```

| 카테고리 | 지표 필드 | 설명 |
|----------|-----------|------|
| `rise` / `fall` / `volume` | `volume`, `amount` | 거래량·거래대금 포함 |
| `amount` | `volume`, `amount` | 거래대금 기준 정렬 |
| `foreign_buy` / `institution_buy` | `net_buy` | 순매수(주) |
| `high_52w` / `low_52w` | `high_52w`, `low_52w` | 52주 신고가·신저가 |

**공통 필드** (모든 카테고리): `stock_code`, `stock_name`, `current_price`, `change_rate`

| 상태코드 | 의미 |
|----------|------|
| 200 | 정상 (KIS API 실패 시에도 캐시 있으면 200, 없으면 `status: error`) |

---

## 빠른 테스트 (curl 예시)

```bash
# 헬스체크
curl http://localhost:8000/api/v1/health

# 추천 종목 조회
curl http://localhost:8000/api/v1/stocks/recommend

# 추천 종목 히스토리 (일별)
curl "http://localhost:8000/api/v1/stocks/history?type=daily"

# 종목 검색
curl "http://localhost:8000/api/v1/stocks/search?q=삼성"

# 종목 상세 조회 (삼성전자)
curl http://localhost:8000/api/v1/stocks/005930/detail

# 추천 종목 수동 업데이트
curl -X POST http://localhost:8000/api/v1/stocks/sync/recommendations

# OHLCV 수동 동기화 (특정 종목)
curl -X POST http://localhost:8000/api/v1/stocks/sync/ohlcv \
  -H "Content-Type: application/json" \
  -d '{"stock_codes": ["005930", "000660"]}'

# 종목 마스터 동기화 (KRX 전체 종목)
curl -X POST http://localhost:8000/api/v1/stocks/sync/master

# 보유 종목 목록
curl http://localhost:8000/api/v1/holdings

# 보유 종목 추가
curl -X POST http://localhost:8000/api/v1/holdings \
  -H "Content-Type: application/json" \
  -d '{"stock_code":"005930","stock_name":"삼성전자","avg_price":68000,"quantity":10}'

# 보유 종목 수정
curl -X PUT http://localhost:8000/api/v1/holdings/1 \
  -H "Content-Type: application/json" \
  -d '{"avg_price":70000,"quantity":15}'

# 보유 종목 삭제
curl -X DELETE http://localhost:8000/api/v1/holdings/1

# 매도 신호 분석
curl http://localhost:8000/api/v1/holdings/1/sell-analysis

# 프로필 목록
curl http://localhost:8000/api/v1/profiles

# 프로필 생성
curl -X POST http://localhost:8000/api/v1/profiles \
  -H "Content-Type: application/json" \
  -d '{"name":"성장주 포트폴리오","analysis_type":"quant"}'

# 포트폴리오 분석 조회 (캐시)
curl "http://localhost:8000/api/v1/portfolio/analysis?profile_id=1"

# 포트폴리오 분석 실행
curl -X POST http://localhost:8000/api/v1/portfolio/analysis \
  -H "Content-Type: application/json" \
  -d '{"profile_id":1}'

```

> 리포트 API 테스트는 ARA 프로젝트(http://localhost:8001) 참조.
