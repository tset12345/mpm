# MPM 가상거래 매수/매도 알고리즘

## 1. 전체 흐름

```
[스케줄러] ──────────────────────────────────────────────────────────
  08:50 / 11:00 / 14:00 / 16:10 (월~금)  →  run_daily_sync()
  10분마다 09:00~15:20 (월~금)            →  run_intraday_trading()

run_daily_sync():
  1. update_recommendations()   → 추천 종목 10개 산출 & DB 저장
  2. virtual_sell_trigger()     → 포지션 매도 조건 검사
  3. virtual_buy_trigger()      → 추천 종목 매수 조건 검사
```

---

## 2. 종목 발굴 (`recommendations.py`)

### 2-1. 수급 조건 5가지 (KIS API, 병렬 수집)
| 조건 | 레이블 | API |
|---|---|---|
| A | 거래대금 | get_trading_amount_ranking() |
| B | 기관·외인 순매수 | get_institution_foreign_net_buy_ranking() |
| C | 거래량 | get_volume_ranking() |
| D | 신고가 근접 | get_new_high_ranking() |
| E | VI 발동 | get_vi_triggered_stocks() |

- 조건별 상위 30개씩 수집, ETF/ETN·동전주(1,000원 미만) 제거
- 중복 허용 없이 union → 최대 ~150개 후보
- 분석 대상 압축: 상위 30개 (`valid_codes = codes[:30]`)

### 2-2. 시장 국면 판단
```
KOSPI 종가 vs MA20
  종가 ≥ MA20 → BULL
  종가 < MA20 → BEAR
```
- BEAR 시장에서는 Engine A 점수 강제 0 (가짜 돌파 위험)

---

## 3. 기술적 점수 산출 (`technical.py`)

### 3-1. Stage 1 — Hard Filter
```
MA20 거래량 < 100,000주  →  즉시 0점 (저유동성 제거)
```

### 3-2. Engine A — 추세 돌파형 (0-100점)

| 조건 | 만점 | 세부 |
|---|---|---|
| 골든크로스 | 15 | MA5>MA20>MA60 정배열 or 최근 3봉 내 교차 → 15; MA5>MA20만 → 8 |
| ADX/DMI 강한 상승추세 | 15 | +DI>-DI + ADX≥25 → 15; ADX≥20 → 10 |
| 일목 구름대 돌파 | 15 | above_cloud → 15; in_cloud → 5 |
| 볼린저 스퀴즈 상단돌파 | 15 | 밴드폭<10% + 종가≥상단 → 15; 밴드폭<10% + 종가>중간 → 6 |
| 전고점 돌파 + 거래량 | 15 | 돌파 + 거래량비율≥1.5 → 15; 돌파만 → 8 |
| OBV 선행 돌파 | 15 | OBV 20일 고점 돌파 + 주가 미돌파(선행) → 15; 동반 돌파 → 8 |
| 거래량 급증 | 10 | 비율≥3.0 → 10; ≥2.0 → 7; ≥1.5 → 3 |

**RSI 처리 (3단계)**
- RSI ≥ 80: Hard Veto → 점수 강제 0 (극과열, 진입 금지)
- RSI 70 최초 돌파 (이전 봉 < 70): +5 (모멘텀 가산)
- RSI ≥ 70 지속: -10 (Soft Veto)

**BEAR 시장**: 점수 무관 즉시 0점

### 3-3. Engine B — 역추세 반등형 (0-100점)

**Pre-filter (둘 다 통과해야)**
- 거래대금(종가×거래량) < 50억 원 → 0점 (유동성 부족)
- MA60 우하향 중(현재 < 5봉 전) → 0점 (칼날 잡기 방지)

**공통 지표**

_과매도 그룹 (max 25점)_
```
RSI < 35 / Stoch %K < 25 / CCI < -80 / MFI < 25
  3개 이상 → 25점   2개 → 20점   1개 → 10점
```

_수요밴드 통합 (max 35점)_
```
볼린저 하단 근처(≤1.02배) / 엔벨로프 하단(≤1.01배) / 피봇 S2(±5%) / 피보나치(±2%)
  2개 이상 → 35점(양봉) / 20점(음봉)
  1개      → 20점(양봉) / 8점(음봉)
```

**B1 — 낙폭과대 V자 반등형** (이격도 < 99%)
```
이격도: <93% → 15점  /  <95% → 12점  /  <97% → 8점  /  기타 → 3점
최종점수 = int((이격도점수 + 과매도점수 + 수요밴드점수) / 75 * 100)
```

**B2 — 정배열 눌림목형** (이격도 ≥ 99%)
```
눌림목 조건: MA5>MA20 + 종가>MA20 + 최근5봉 저가 중 MA20±2% 접촉
  양봉 → 25점  /  음봉 → 12점
최종점수 = int((과매도점수 + 수요밴드점수 + 눌림목점수) / 85 * 100)
```

### 3-4. 최종 점수
```
score = max(engine_a_score, engine_b_score)
engine = 높은 쪽 (동점 시 A)
Top 10 = score ≥ 20점 기준, 점수 내림차순 상위 10개
```

---

## 4. 일목균형표 (`ichimoku.py`)
```
전환선 = (9일 최고 + 9일 최저) / 2
기준선 = (26일 최고 + 26일 최저) / 2
선행스팬A = (전환선 + 기준선) / 2
선행스팬B = (52일 최고 + 52일 최저) / 2

종가 > max(A, B)  →  above_cloud  (+15점, Engine A)
종가 < min(A, B)  →  below_cloud
그 외              →  in_cloud     (+5점, Engine A)
```

---

## 5. 매수 트리거 (`virtual_trading.py`)

### 5-1. 계좌 설정값
| 파라미터 | 기본값 | 의미 |
|---|---|---|
| min_score | 50 | 매수 최소 점수 |
| max_positions | 5 | 최대 보유 종목 수 |
| position_size | 20% | 1종목당 현금 비율 |
| stop_loss_pct | 10% | 공통 손절 기준 |
| take_profit_pct | 20% | 공통 익절 기준 |
| strategy | both | engine_a / engine_b / both |

### 5-2. 매수 조건 체크 순서
```
1. score < min_score          → 스킵
2. 이미 보유 중               → 스킵
3. 당일 손절된 종목           → 스킵 (재매수 금지)
4. 전략 필터:
     strategy=engine_a  →  engine_a_score > 0 필요 (engine="A")
     strategy=engine_b  →  engine_b_score > 0 필요 (engine="B")
     strategy=both      →  태그 기반 ("추세 돌파형"→A, "역추세 반등형"→B)
5. current_price 없음         → 스킵
6. 포지션 수 ≥ max_positions  → 중단
```

### 5-3. 매수 체결 계산
```
투자금액 = current_cash × position_size / 100
수량     = floor(투자금액 / price)
체결금액 = 수량 × price

저장: virtual_positions (entry_atr, entry_low, highest_price)
      virtual_trades (side="buy", engine, tech_score)
      virtual_accounts (current_cash 차감)
```

---

## 6. 매도 트리거 (`virtual_trading.py`)

### 6-1. 공통 손절·익절 (모든 엔진, 먼저 체크)
```
change_rate = (현재가 - avg_price) / avg_price * 100

change_rate ≤ -stop_loss_pct   →  stop_loss    (기본 -10%)
change_rate ≥ +take_profit_pct →  take_profit  (기본 +20%)
```

### 6-2. Engine A 청산 조건
```
1. ATR 하드 스탑
   현재가 < avg_price - 1.5 × entry_atr  →  atr_hard_stop

2. ATR 트레일링 스탑
   보유 중 highest_price 갱신 유지
   현재가 < highest_price - 2.0 × 현재ATR  →  atr_trailing_stop

3. RSI 모멘텀 소멸
   이전봉 RSI > 70  AND  현재봉 RSI ≤ 70  →  rsi_exhaustion
```

### 6-3. Engine B 청산 조건
```
1. 진입 저점 이탈
   현재가 < entry_low  →  entry_low_breach  (전략 전제 붕괴)

2. 보유 기간 초과 + 손실
   holding_days ≥ 5  AND  현재가 ≤ avg_price  →  time_limit_stop

3. MA20 첫 터치 분할 익절
   half_exited=False  AND  전일종가 < MA20 ≤ 현재가  →  ma20_half_exit (보유량 50%)

4. 목표 도달 전량 익절
   이격도 ≥ 102%  OR  RSI ≥ 60  →  target_reached
```

### 6-4. 매도 유형 요약
| trigger_type | 엔진 | 의미 |
|---|---|---|
| stop_loss | 공통 | 고정 손절 (-10%) |
| take_profit | 공통 | 고정 익절 (+20%) |
| atr_hard_stop | A | ATR 하드 스탑 (진입가 - 1.5ATR) |
| atr_trailing_stop | A | ATR 트레일링 스탑 (고점 - 2.0ATR) |
| rsi_exhaustion | A | RSI 모멘텀 소멸 (70+ → 70-) |
| entry_low_breach | B | 진입 저점 이탈 |
| time_limit_stop | B | 보유 5일 + 손실 |
| ma20_half_exit | B | MA20 최초 도달 분할 익절 |
| target_reached | B | 이격도102% 또는 RSI60 도달 |
| manual | - | 수동 체결 |
| algo_buy | - | 알고리즘 매수 (trigger_type for buy) |

---

## 7. 매도 신호 분석 (`sell_signal.py`, 참고용)

포지션 상세 화면 표시용 분석 (가상거래 자동 청산과 별개).

```
sell_score = 기술적 신호 + 엔진별 신호 + 기본적 신호 + 자산관리 신호 (min 100)

등급:
  0~20   →  관망
  21~40  →  주의
  41~65  →  매도 검토
  66+    →  즉시 매도
```

**기술적 신호 가산점**
- MA5/20 데드크로스: 20점
- MA20/60 데드크로스: 25점
- RSI >80: 15점 / >70: 8점
- 스토캐스틱 과매수 데드크로스: 10점
- 장대음봉 + 대량 거래: 12점
- MACD 데드크로스: 10점
- 주가 MA60 하회: 8점 / MA20 하회: 5점

---

> **알고리즘 성능 현황 및 개선 검토 포인트** → `01_HISTORY.md` §알고리즘 성능 현황
