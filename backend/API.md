# MPM Backend API Reference

## 기본 정보

| 항목 | 값 |
|------|-----|
| Base URL | `http://localhost:8000` |
| API 버전 접두어 | `/api/v1` |
| 응답 형식 | `application/json` |
| 인증 | 없음 (내부망 전용) |
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |

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

## 내부 서비스 구조 참고

### 기술적 분석 엔진 (`services/technical.py`)

`analyze(records, cloud_position) → {"score": int, "tags": list, "signals": dict, "score_detail": dict, "strength": str}`

**스코어링: 4개 카테고리 × 최대 10점 = 40점 → ×2.5 → 0–100 환산**

| 카테고리 | 내용 | 최대 점수 |
|----------|------|-----------|
| **A. 추세 (Trend)** | 이동평균 골든크로스, MA20/MA60 위치, 일목균형표 구름대 위치 | 10 |
| **B. 모멘텀 (Momentum)** | MACD 교차 및 방향, RSI 과매도 탈출/수준, 스토캐스틱 | 10 |
| **C. 변동성 (Volatility)** | 볼린저밴드 위치, 이격도, 전고점 돌파 | 10 |
| **D. 거래량 (Volume)** | 거래량 급증, 이동평균 대비 거래량, 거래량 추세 | 10 |

`strength` 값:
- `"강세"`: score ≥ 60
- `"중립"`: 40 ≤ score < 60
- `"약세"`: score < 40

---

### 매도 신호 분석 (`services/sell_signal.py`)

`analyze_sell(records, avg_price, current_price, per, pbr, eps, w52_high, portfolio_weight)`

3개 관점 통합 분석:
- **기술적**: 데드크로스, RSI 과매수(>70), 볼린저 상단 이탈, MACD 하향 교차
- **기본적**: PER/PBR 과열, 52주 신고가 대비 고점 근접
- **자산관리**: 단일 종목 비중 30% 초과, 수익률 목표 달성(+20% 이상)

---

### KIS API 클라이언트 (`services/kis_api.py`)

FastAPI 시작 시 싱글턴 `kis_client` 인스턴스 생성. 첫 API 호출 시 OAuth2 토큰 자동 발급 후 파일 캐시(`.kis_token_cache.json`) 및 메모리 캐시에 저장. 만료 300초 전 자동 재발급.

| 메서드 | KIS TR ID | 설명 |
|--------|-----------|------|
| `get_stock_price(stock_code)` | `FHKST01010100` | 현재가·PER·PBR·EPS·BPS·ROE 조회 |
| `get_daily_ohlcv(stock_code, start, end)` | `FHKST03010100` | 일별 OHLCV 차트 조회 |
| `get_volume_ranking()` | `FHPST01700000` | 거래량 순위 조회 (실서버 전용) |

---

### 스케줄러 (`services/scheduler.py`)

- 엔진: APScheduler `AsyncIOScheduler` (Asia/Seoul 타임존)
- 시작 체크: 서버 기동 시 당일 추천 종목 없으면 즉시 업데이트
- 실행 일정 (평일):
  - **08:50 KST**: 전일 마감 데이터 기반 추천 종목 갱신
  - **16:10 KST**: 당일 장마감 후 추천 종목 업데이트 + OHLCV 동기화 + 히스토리 저장

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
