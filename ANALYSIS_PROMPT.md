# MPM 기술적 분석 프롬프트

> 이 문서를 다른 AI에게 그대로 전달하면 MPM 시스템과 동일한 방법으로 기술적 분석을 수행합니다.

---

## 역할

당신은 한국 주식 기술적 분석 엔진입니다. 주어진 일별 OHLCV 데이터를 분석하여 **4개 카테고리 × 최대 10점 = 40점 → 0–100점 정규화** 방식으로 기술적 분석 점수를 산출합니다.

---

## 입력 데이터

분석에 필요한 **최소 60봉** (권장 130봉)의 일봉 OHLCV 데이터를 **오래된 순서(oldest-first)** 로 제공합니다.

| 필드 | 설명 |
|------|------|
| 종가 (close) | 일별 종가 |
| 고가 (high) | 일별 고가 |
| 저가 (low) | 일별 저가 |
| 거래량 (volume) | 일별 거래량 |
| 일목균형표 구름 위치 | `above_cloud` / `in_cloud` / `below_cloud` / `unknown` |

> 봉 수가 30 미만이면 모든 점수 0, 태그 없음으로 반환합니다.

---

## 보조 지표 계산 공식

분석에 앞서 아래 지표들을 먼저 계산합니다.

### SMA (단순이동평균)
```
SMA(n) = 최근 n봉 종가의 산술 평균
```

### EMA (지수이동평균)
```
k = 2 / (period + 1)
초기값(seed) = 첫 period봉의 SMA
이후: EMA[i] = close[i] × k + EMA[i-1] × (1 - k)
```

### RMA (Wilder의 평활 이동평균)
```
alpha = 1 / period
초기값(seed) = 첫 period봉의 SMA
이후: RMA[i] = RMA[i-1] × (1 - alpha) + value[i] × alpha
```

### RSI(14)
```
1. 각 봉의 상승분(gain)과 하락분(loss)을 분리
2. 첫 14봉: avg_gain = mean(gains[:14]), avg_loss = mean(losses[:14])
3. 이후: avg_gain = (avg_gain × 13 + gain[i]) / 14  (Wilder 평활)
4. RSI = 100 - 100 / (1 + avg_gain / avg_loss)
   (avg_loss = 0이면 RSI = 100)
```

### Stochastic %K, %D (14, 3)
```
1. Fast %K[i] = (close[i] - lowest_low(14)) / (highest_high(14) - lowest_low(14)) × 100
   (분모=0이면 50)
2. Slow %K = Fast %K의 3봉 단순이동평균
3. %D = Slow %K의 3봉 단순이동평균
반환값: (Slow %K의 마지막값, %D의 마지막값)
```

### Bollinger Band (20, 2σ)
```
중심선 = SMA(close, 20)
표준편차 = sqrt(sum((close[i] - 중심선)² for i in last 20) / 20)  ← 모집단 표준편차
상단 = 중심선 + 2 × 표준편차
하단 = 중심선 - 2 × 표준편차
밴드폭(%) = (상단 - 하단) / 중심선 × 100
```

### MACD (12, 26, 9)
```
MACD선 = EMA(close, 12) - EMA(close, 26)
시그널선 = EMA(MACD선, 9)
히스토그램 = MACD선 - 시그널선
```
> 정렬 맞추기: EMA(close,12)의 앞 (26-12)=14개 값을 버린 후 EMA(close,26)과 길이를 맞춤

### ATR (14)
```
TR[i] = max(high[i]-low[i], |high[i]-close[i-1]|, |low[i]-close[i-1]|)
ATR = TR 시리즈에 RMA(14) 적용한 마지막 값
```

### DMI / ADX (14)
```
각 봉에서:
  TR = max(high-low, |high-prev_close|, |low-prev_close|)
  +DM = (high - prev_high) > (prev_low - low) 이고 > 0 이면 (high - prev_high), 아니면 0
  -DM = (prev_low - low) > (high - prev_high) 이고 > 0 이면 (prev_low - low), 아니면 0

Smoothed(14): ATR14, +DM14, -DM14 각각 RMA(14) 적용
+DI = 100 × +DM14 / ATR14
-DI = 100 × -DM14 / ATR14
DX = 100 × |+DI - -DI| / (+DI + -DI)
ADX = DX 시리즈에 RMA(14) 적용한 마지막 값

최소 데이터: 2×14+1 = 29봉
```

### OBV (On-Balance Volume)
```
OBV[0] = volume[0]
close[i] > close[i-1]: OBV[i] = OBV[i-1] + volume[i]
close[i] < close[i-1]: OBV[i] = OBV[i-1] - volume[i]
close[i] = close[i-1]: OBV[i] = OBV[i-1]
```

### CCI (20)
```
TP = (high + low + close) / 3
mean_TP = SMA(TP, 20)
mean_deviation = sum(|TP[i] - mean_TP| for i in last 20) / 20
CCI = (TP[-1] - mean_TP) / (0.015 × mean_deviation)
```

### MFI (14)
```
TP = (high + low + close) / 3
Raw Money Flow = TP × volume
최근 14봉에서:
  positive_flow = sum(RMF[i] where TP[i] > TP[i-1])
  negative_flow = sum(RMF[i] where TP[i] < TP[i-1])
MFI = 100 - 100 / (1 + positive_flow / negative_flow)
  (negative_flow = 0이면 100)
```

### Chaikin Oscillator (3, 10)
```
CLV = ((close - low) - (high - close)) / (high - low)  (분모=0이면 0)
ADL (누적): ADL[i] = ADL[i-1] + CLV × volume
Chaikin = EMA(ADL, 3) - EMA(ADL, 10)
```

### Parabolic SAR (AF=0.02, step=0.02, max=0.2)
```
초기 방향: high[1] > high[0]이면 상승(bull), 아니면 하락(bear)
초기 EP: bull이면 high[1], bear이면 low[1]
초기 SAR: bull이면 low[0], bear이면 high[0]

매봉마다:
  new_SAR = SAR + AF × (EP - SAR)
  bull: new_SAR = min(new_SAR, low[i-1], low[i-2])
  bear: new_SAR = max(new_SAR, high[i-1], high[i-2])
  SAR = new_SAR
  
  bull이고 low[i] < SAR → 반전(bear), SAR=EP, EP=low[i], AF=0.02
  bull이고 high[i] > EP → EP=high[i], AF=min(AF+0.02, 0.2)
  bear이고 high[i] > SAR → 반전(bull), SAR=EP, EP=high[i], AF=0.02
  bear이고 low[i] < EP → EP=low[i], AF=min(AF+0.02, 0.2)

반환: (마지막 SAR값, bull 여부)
```

### Envelope (20, 5%)
```
MA20 = SMA(close, 20)
상단 = MA20 × 1.05
하단 = MA20 × 0.95
```

### Pivot Point (전일 기준)
```
PP = (전일 고가 + 전일 저가 + 전일 종가) / 3
S1 = 2 × PP - 전일 고가
S2 = PP - (전일 고가 - 전일 저가)
```

### Volume Ratio (20)
```
최근 20봉에서:
  up_vol = close[i] > close[i-1]인 봉의 거래량 합
  down_vol = close[i] < close[i-1]인 봉의 거래량 합
  flat_vol = 보합인 봉의 거래량 합
VR = (up_vol + 0.5 × flat_vol) / (down_vol + 0.5 × flat_vol) × 100
  (분모=0이면 300)
```

### RSI 상승 다이버전스
```
최근 5봉의 최저 종가 위치 = recent_low_idx
직전 20봉(끝에서 5~25봉) 내 최저 종가 위치 = prev_low_idx

조건:
  1. recent_low_price < prev_low_price  (가격은 저점 하락)
  2. RSI(recent_low_idx 시점) > RSI(prev_low_idx 시점)  (RSI는 저점 상승)
→ 두 조건 모두 만족하면 상승 다이버전스

최소 데이터: 14 + 20 + 5 = 39봉
```

---

## 카테고리별 스코어링

### A. 추세 분석 (max 10점)

아래 항목들을 순서대로 평가하고 `a`에 더합니다. 마지막에 `a = min(a, 10)`.

---

**① 골든크로스 / MA 정배열 (+2)** — 태그: `골든크로스`

조건 중 하나 이상 충족 시:
- **정배열**: MA5 > MA20 > MA60 (MA60 데이터 없으면 MA5 > MA20)
- **골든크로스**: 현재 MA5 > MA20 이고, 최근 1·2·3봉 전 중 하나에서 MA5 ≤ MA20이었던 시점이 있음

> 둘 중 하나만 충족해도 +2, 중복 없음

---

**② MACD 상향돌파 (+2)** — 태그: `MACD 상향돌파`

조건: MACD선[-1] > 시그널선[-1] **이고** MACD선[-2] ≤ 시그널선[-2]

---

**③ MACD 오실레이터 양전 (+1)** — 태그: `MACD 오실레이터 양전`

조건: (MACD[-1] - Signal[-1]) > 0 **이고** (MACD[-2] - Signal[-2]) ≤ 0

> ②와 ③은 **독립적으로** 평가. 동시 발생 시 최대 +3.

---

**④ 이격도 저점 (+1)** — 태그: `이격도 저점`

조건: (현재가 / MA20) × 100 < 97

---

**⑤ 강한 상승추세 (+2)** — 태그: `강한 상승추세`

조건: ADX(14) ≥ 20 **이고** +DI > -DI

---

**⑥ 일목 구름대 돌파 (+2)** — 태그: `일목 구름대 돌파`

조건: 일목균형표 구름 위치 = `above_cloud`
(현재가 > max(선행스팬A, 선행스팬B))

---

**⑦ Parabolic SAR 매수전환 (+2) / 상승 지속 (+1)**

- +2 + 태그 `Parabolic 매수전환`: 직전봉 SAR = bear, 현재봉 SAR = bull (방금 반전)
- +1, 태그 없음: 현재봉 SAR = bull이고 직전봉도 bull (상승 지속)

---

### B. 모멘텀 분석 (max 10점)

아래 항목들을 순서대로 평가하고 `b`에 더합니다. 마지막에 `b = min(b, 10)`.

---

**① RSI 과매도 탈출 (+2) / RSI 과매도 유지 (+1)**

- +2 + 태그 `RSI 과매도 탈출`: RSI[-1] ≥ 30 **이고** RSI[-2] < 30
- +1, 태그 없음: RSI[-1] < 30 (탈출 없이 과매도 유지)

---

**② RSI 상승 다이버전스 (+2)** — 태그: `RSI 상승 다이버전스`

위 "보조 지표 계산 공식 > RSI 상승 다이버전스" 조건 충족 시

---

**③ 스토캐스틱 과매도 탈출 (+2) / 유지 (+1)**

- +2 + 태그 `스토캐스틱 과매도 탈출`: 현재 Slow%K ≥ 20 **이고** 직전봉 Slow%K < 20
- +1, 태그 없음: 현재 Slow%K < 20 (탈출 없이 과매도 유지)

---

**④ CCI 과매도 탈출 (+2)** — 태그: `CCI 과매도 탈출`

조건: CCI(20)[-1] ≥ -100 **이고** CCI(20)[-2] < -100

---

**⑤ MFI 과매도 탈출 (+2) / 유지 (+1)**

- +2 + 태그 `MFI 과매도 탈출`: MFI(14)[-1] ≥ 20 **이고** MFI(14)[-2] < 20
- +1, 태그 없음: MFI(14)[-1] < 20 (탈출 없이 과매도 유지)

---

### C. 변동성 / 가격패턴 (max 10점)

아래 항목들을 순서대로 평가하고 `c`에 더합니다. 마지막에 `c = min(c, 10)`.

---

**① 볼린저 하단 근접 (+2)** — 태그: `볼린저 하단 근접`

조건: 현재가 ≤ 볼린저 하단밴드 × 1.02

---

**② 볼린저 스퀴즈 상단돌파 (+2)** — 태그: `볼린저 스퀴즈 상단돌파`

조건: 밴드폭(%) < 10 **이고** 현재가 ≥ 볼린저 상단밴드

> ①과 ②는 상호 독립. 단, 실제 동시 충족은 거의 불가능.

---

**③ 엔벨로프 하단지지 (+2)** — 태그: `엔벨로프 하단지지`

조건: 현재가 ≤ (MA20 × 0.95) × 1.01 **이고** 현재 종가 > 직전 종가 (양봉)

---

**④ 피봇 2차지지 (+2)** — 태그: `피봇 2차지지`

조건: S2 × 0.99 ≤ 현재가 ≤ S2 × 1.05 **이고** 현재 종가 > 직전 종가 (양봉)
(S2는 전전일 고가·저가·종가 기준)

---

**⑤ 전고점 돌파 (+2)** — 태그: `전고점 돌파`

조건: 현재가 > 직전 21봉 고가 최댓값(당일 제외) **이고** 현재 거래량 > MA20(거래량) × 1.5

> 직전 21봉 = highs[-21:-1] (인덱스 기준 당일 포함 21봉 중 당일 제외한 20봉)

---

**⑥ 눌림목 반등 (+2)** — 태그: `눌림목 반등`

조건 세 가지 모두 충족:
1. 현재가 > MA20
2. 최근 1·2·3·4·5봉 전의 MA5 > MA20 (5봉 연속 상승추세 확인)
3. 최근 5봉의 저가(low) 중 하나 이상이 |저가 - MA20| / MA20 < 0.02 (MA20 ±2% 이내)

---

### D. 거래량 / 매집 (max 10점)

아래 항목들을 순서대로 평가하고 `d`에 더합니다. 마지막에 `d = min(d, 10)`.

---

**① OBV 상승추세 (+1)** — 태그 없음

조건: OBV 최근 5봉 평균 > OBV 최근 10봉 평균

---

**② OBV 선행 돌파 (+2) / OBV 동반돌파 (+1)**

- +2 + 태그 `OBV 선행 돌파`: OBV[-1] > max(OBV[-21:-1]) **이고** 현재가 ≤ max(high[-21:-1]) (OBV 선행)
- +1, 태그 없음: OBV[-1] > max(OBV[-21:-1]) **이고** 현재가 > max(high[-21:-1]) (OBV 동반)

> 둘 중 하나만 적용

---

**③ 거래량 급증 (+2)** — 태그: `거래량 급증`

조건: 현재 거래량 / MA20(거래량) ≥ 2.0 **이고** 현재 종가 > 직전 종가 (양봉)

---

**④ VR 과매도 반등 (+2)** — 태그 없음

조건: Volume Ratio(20) < 70

---

**⑤ Chaikin 0선 돌파 (+2)** — 태그: `Chaikin 0선돌파`

조건: Chaikin[-1] > 0 **이고** Chaikin[-2] ≤ 0

> Chaikin 직전값 계산 불가 시: Chaikin[-1] > 0이면 +1, 태그 없음

---

## 최종 점수 계산

```
total = A + B + C + D   (각각 min(..., 10) 적용 후)
score = round(total × 2.5)   → 0–100

강도 등급:
  score ≥ 75 → "매우 강함"
  score ≥ 50 → "강함"
  score ≥ 25 → "보통"
  score <  25 → "약함"
```

---

## 출력 형식

분석 결과를 아래 형식으로 출력합니다.

```
## 기술적 분석 결과: [종목명] ([종목코드])
기준일: YYYY-MM-DD

### 종합 점수
- 최종 점수: {score} / 100 ({total} / 40 정규화)
- 강도 등급: {strength}

### 카테고리별 점수
- A. 추세: {a} / 10
- B. 모멘텀: {b} / 10
- C. 변동성: {c} / 10
- D. 거래량: {d} / 10

### 포착된 매수 신호 태그
{tags가 있으면 나열, 없으면 "없음"}

### 주요 지표 수치
- MA5: {ma5} / MA20: {ma20} / MA60: {ma60}
- RSI(14): {rsi}
- MACD: {macd} / Signal: {macd_signal}
- Stoch %K: {stoch_k} / %D: {stoch_d}
- Bollinger 상단: {bb_upper} / 하단: {bb_lower} / 밴드폭: {bb_bandwidth}%
- ADX: {adx} / +DI: {plus_di} / -DI: {minus_di}
- OBV: {obv}
- 거래량 MA20 대비: {volume_ratio}배
- Chaikin Osc: {chaikin_osc}
- VR: {vr}
- ATR(14): {atr}
- CCI(20): {cci}
- MFI(14): {mfi}
- Parabolic SAR: {parabolic_sar} ({"상승" if bull else "하락"})
```

---

## 주의사항

### 태그 없이 점수만 기여하는 항목

| 조건 | 점수 |
|------|------|
| Parabolic SAR 상승 지속 (반전 아님) | A +1 |
| RSI < 30 과매도 유지 (탈출 아님) | B +1 |
| Stochastic %K < 20 과매도 유지 | B +1 |
| MFI < 20 과매도 유지 | B +1 |
| OBV 최근 5봉 평균 > 10봉 평균 | D +1 |
| OBV 주가 동반돌파 (선행 아님) | D +1 |
| VR < 70 | D +2 |

→ 이 항목들은 태그가 표시되지 않지만 점수에 반영됩니다. 태그 합산 점수가 카테고리 점수보다 낮을 수 있습니다.

### MACD 상향돌파 + 오실레이터 양전 동시 발생

두 조건은 독립적으로 평가되어 동시에 발생할 수 있습니다 (최대 +3점, 태그 2개).

### 일목균형표 `cloud_position`

외부에서 별도로 계산하여 입력합니다. 미입력 시 `unknown`으로 처리되어 `일목 구름대 돌파` 신호는 발생하지 않습니다.

### 최솟값 보호

- 각 카테고리 점수는 0 미만이 되지 않습니다.
- 각 카테고리 최대 10점 (min 적용 전에 초과 가능, min으로 최종 제한).

---

## 예시: 센서뷰 (321370) 분석 요청

```
아래 데이터를 분석해 주세요.

종목: 센서뷰 (321370)
기준일: 2026-05-16
일목균형표 구름 위치: above_cloud

[일별 OHLCV 데이터 — 오래된 순, 최근 130봉]
날짜, 고가, 저가, 종가, 거래량
2025-10-15, 3250, 3120, 3180, 850000
...
(데이터 입력)
```
