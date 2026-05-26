import asyncio
import hashlib
import json
import logging
from datetime import date, datetime
from typing import Optional

import google.generativeai as genai
from app.core.config import settings

logger = logging.getLogger(__name__)
genai.configure(api_key=settings.gemini_api_key)
_model = genai.GenerativeModel("gemini-2.5-flash-lite")


def compute_holdings_hash(holdings: list[dict]) -> str:
    """보유 종목 (코드·수량·단가) 기반 MD5 해시 — 변경 감지용."""
    data = sorted(
        [{"c": h["stock_code"], "q": h["quantity"], "a": h["avg_price"]} for h in holdings],
        key=lambda x: x["c"],
    )
    return hashlib.md5(json.dumps(data, sort_keys=True).encode()).hexdigest()[:16]


def _holdings_lines(holdings: list[dict]) -> tuple[str, int, int]:
    """공통 종목 리스트 텍스트 + 원금·평가금액 반환."""
    total_purchase = sum(h["avg_price"] * h["quantity"] for h in holdings)
    total_val = sum(
        (h.get("eval_amount") or h["avg_price"] * h["quantity"]) for h in holdings
    )
    lines = []
    for h in sorted(holdings, key=lambda x: -(x.get("eval_amount") or x["avg_price"] * x["quantity"])):
        val = h.get("eval_amount") or h["avg_price"] * h["quantity"]
        weight = val / total_val * 100 if total_val else 0
        profit_rate = h.get("profit_rate")
        profit_str = (
            f"  |  수익률: {'+' if profit_rate >= 0 else ''}{profit_rate:.1f}%"
            if profit_rate is not None else ""
        )
        cp = h.get("current_price")
        price_str = f"  |  현재가: {cp:,}원" if cp else ""
        lines.append(
            f"- {h['stock_name']} ({h['stock_code']}): {weight:.1f}%"
            f"  |  평균단가: {h['avg_price']:,}원"
            f"{price_str}{profit_str}"
        )
    return "\n".join(lines), total_purchase, total_val


def _build_prompt_quant(holdings: list[dict], profile_name: str) -> str:
    holdings_text, _, _ = _holdings_lines(holdings)

    return f"""# Role
너는 세계적인 자산운용사의 수석 포트폴리오 매니저이자 퀀트 분석가이다. 사용자가 제공한 주식 포트폴리오 데이터를 바탕으로 현대 포트폴리오 이론(MPT) 및 위험 관리 기법을 적용하여 [포트폴리오 진단 및 최적화 리포트]를 작성해야 한다.

---

## 1. 포트폴리오 분석 및 진단 기준

### A. 자산 배분 및 집중도 분석 (Asset Allocation)
- 특정 종목, 특정 섹터(예: 테크, 바이오, 금융 등), 특정 국가에 자산이 과도하게 집중되었는지 평가한다.
- 개별 종목 비중이 20%를 초과하거나, 특정 섹터 비중이 40%를 초과하는 경우 리스크 경고를 부여한다.

### B. 종목 간 상관관계 및 분산 효과 (Correlation & Diversification)
- 보유 종목들이 동반 하락할 위험이 있는지(예: 기술주와 레버리지 ETF의 동시 보유 등) 상관관계를 추정한다.
- 시장 하락 시 포트폴리오를 방어할 수 있는 자산(방어주, 현금, 채권 등)의 비중이 적절한지 진단한다.

### C. 위험 대비 수익성 평가 (Risk-Adjusted Return)
- 포트폴리오의 전체적인 변동성(Beta)과 위험 대비 수익률(Sharpe Ratio) 성향을 추정한다.
- 고위험·고수익(High Risk, High Return) 성향인지, 안정형 성향인지 분류하고 현재 시장 상황에 적합한지 평가한다.

### D. 리밸런싱 가이드 (Rebalancing)
- 현재 비중을 유지해야 할 종목, 수익 실현을 통해 비중을 줄여야 할 종목, 저가 매수로 비중을 늘려야 할 종목을 명확히 구분한다.

---

## 2. 입력 데이터

[보유 종목 리스트 및 비중]
{holdings_text}

[투자 성향 / 목표]: 중장기 자산 증식
[투자 기간]: 1년 이상 중장기

---

## 3. 출력 포맷
반드시 아래 형식으로만 답변하라. 감정적인 평가는 배제하고 철저히 데이터와 리스크 관점으로 기술한다.

**📊 {profile_name}의 주식 포트폴리오 분석 보고서**

- **1. 포트폴리오 현황 요약**
  - 총 보유 종목 수: X개
  - 주요 집중 섹터: [섹터명] (X%) / [섹터명] (X%)
  - 포트폴리오 위험 성향: [고위험 공격형 / 중위험 성장형 / 저위험 방어형]

- **2. 핵심 리스크 진단 (문제점)**
  - 🚨 *위험 요인 1:* (예: 반도체 섹터 비중이 40%로 높아 업황 악화 시 치명적임)
  - 🚨 *위험 요인 2:* (예: 종목 간 상관관계가 너무 높아 분산 투자 효과가 미미함)

- **3. 포트폴리오 최적화 제안 (액션 플랜)**
  - **축소 권고(익절/손절):** [종목명] (현재 X% → 목표 X%로 축소 권고 / 사유: 변동성 관리)
  - **확대 권고(추가매수):**
    - [보유 종목 확대] [종목명] (현재 X% → 목표 X%로 확대 / 사유: 헤지 및 방어력 강화) — 해당 없을 경우 생략
    - **신규 편입 추천 종목 (1~3개):** 현재 포트폴리오의 약점을 보완할 수 있는 한국 주식(코스피·코스닥) 또는 ETF를 구체적으로 추천한다.
      - [종목명 (종목코드)] — 추천 사유: [섹터 헤지 / 분산 효과 / 위험 조정 수익률 개선 등 근거]
      - [종목명 (종목코드)] — 추천 사유: ...

- **4. 최종 매니저 한줄평**
  - 목표로 하는 중장기 자산 증식을 달성하기 위해 현재 포트폴리오는 **[조정 필수 / 유지 가능 / 적극 변경]** 상태입니다.
"""


def _build_prompt_dividend(holdings: list[dict], profile_name: str) -> str:
    holdings_text, total_purchase, total_val = _holdings_lines(holdings)

    # 배당률 조회 지시가 포함된 종목 리스트 재생성
    dividend_lines = []
    for line in holdings_text.split("\n"):
        dividend_lines.append(line + "  |  배당률: 최근 공시 기준으로 직접 조회하여 반영")
    holdings_with_div = "\n".join(dividend_lines)

    return f"""# Role
너는 세계적인 자산운용사의 수석 포트폴리오 매니저이자 배당 성장 투자의 대가이다. 사용자가 제공한 주식 포트폴리오 데이터와 배당 정보를 바탕으로 현대 포트폴리오 이론(MPT) 및 배당 가치 평가 기법을 적용하여 [배당 특화 포트폴리오 진단 및 최적화 리포트]를 작성해야 한다.

---

## 1. 포트폴리오 분석 및 진단 기준

### A. 자산 배분 및 집중도 분석 (Asset Allocation)
- 특정 종목, 특정 섹터(예: 빅테크, 고배당 REITs, 금융 등)에 자산이 과도하게 집중되었는지 평가한다.
- 개별 종목 비중이 20%를 초과하거나, 특정 섹터 비중이 40%를 초과하는 경우 리스크 경고를 부여한다.

### B. 종합 배당 수익률 및 현금흐름 분석 (Dividend Analysis)
- 포트폴리오의 **[세전 가중평균 배당 수익률]**을 계산한다. (각 종목의 배당률 × 보유 비중 합산)
- 투자 원금 대비 연간 예상 세전/세후 배당금 총액을 산출하여 매달 실질적으로 들어오는 현금흐름 요약을 제공한다.
- 배당 안정성(배당 성향, 배당 삭감 리스크)과 배당 성장성(연평균 배당 성장률)을 종합 평가한다.

### C. 종목 간 상관관계 및 분산 효과 (Correlation & Diversification)
- 고배당주와 성장주 간의 주가 상관관계를 추정하여, 하락장에서 포트폴리오가 실제로 방어력을 가질 수 있는지 진단한다.

### D. 위험 대비 수익성 평가 (Risk-Adjusted Return)
- 포트폴리오의 전체적인 변동성(Beta)을 추정하고, '자본 차익(주가 상승)'과 '배당 수익'의 밸런스가 사용자의 투자 목적에 부합하는지 분류한다.

### E. 리밸런싱 가이드 (Rebalancing)
- 배당 컷(삭감) 위험이 있거나 고평가된 종목은 비중 축소를, 배당 성장성이 높거나 낙폭이 과대해진 고배당주는 비중 확대를 제안한다.

---

## 2. 입력 데이터

[투자 총 원금]: {total_purchase:,}원 (현재 평가금액: {total_val:,}원)

[보유 종목 리스트 / 비중 / 개별 배당률]
(배당률을 모르는 경우 가장 최근 공시 데이터를 찾아 반영하라.)
{holdings_with_div}

[투자 성향 / 목표]: 중장기 배당 성장 및 자산 증식

---

## 3. 출력 포맷
반드시 아래 형식으로만 답변하라. 감정적인 평가는 배제하고 철저히 데이터와 현금흐름 관점으로 기술한다.

**📊 {profile_name}의 배당 특화 포트폴리오 분석 보고서**

- **1. 포트폴리오 및 배당 현황 요약**
  - 총 보유 종목 수: X개
  - **포트폴리오 가중평균 배당 수익률:** 세전 연 X.XX% (세후 연 X.XX%)
  - **연간 예상 배당금 총액:** 세전 총 X,XXX,XXX원 (월평균 약 X,XXX원)
  - 포트폴리오 성향: [고배당 집중형 / 배당성장 균형형 / 고성장 배당소외형]

- **2. 핵심 리스크 및 배당 진단 (문제점)**
  - 🚨 *위험 요인 1:* (예: 특정 고배당 종목의 비중이 높아 해당 기업 배당 삭감 시 타격이 큼)
  - 🚨 *위험 요인 2:* (예: 배당률은 높으나 주가 성장성이 정체되어 물가상승률 방어가 어려움)

- **3. 포트폴리오 최적화 제안 (액션 플랜)**
  - **축소 권고(비중 조절):** [종목명] (현재 X% → 목표 X%로 축소 / 사유: 배당 지속성 의문 및 밸류에이션 부담)
  - **확대 권고(추가매수 / 배당 강화):**
    - [보유 종목 확대] [종목명] (현재 X% → 목표 X%로 확대 / 사유: 배당 성장률 우수 및 방어력 확보) — 해당 없을 경우 생략
    - **신규 편입 추천 종목 (1~3개):** 배당 수익률·배당 성장률·안정성 기준으로 현재 포트폴리오를 보완할 수 있는 한국 주식(코스피·코스닥) 또는 고배당 ETF를 구체적으로 추천한다.
      - [종목명 (종목코드)] — 배당률: 연 X.X% / 추천 사유: [배당 안정성 / 성장률 / 섹터 분산 근거]
      - [종목명 (종목코드)] — 배당률: 연 X.X% / 추천 사유: ...

- **4. 최종 매니저 한줄평**
  - 목표로 하는 중장기 배당 성장 및 자산 증식을 달성하기 위해 현재 포트폴리오는 **[조정 필수 / 유지 가능 / 적극 변경]** 상태입니다.
"""


async def run_analysis(holdings: list[dict], profile_name: str, analysis_type: str = "quant") -> str:
    """Gemini로 포트폴리오 분석 텍스트 생성."""
    if analysis_type == "dividend":
        prompt = _build_prompt_dividend(holdings, profile_name)
    else:
        prompt = _build_prompt_quant(holdings, profile_name)
    response = await asyncio.to_thread(_model.generate_content, prompt)
    return response.text.strip()


def is_stale(row: dict, current_hash: str) -> bool:
    """분석 결과가 오늘 날짜가 아니거나 보유 종목이 변경됐으면 True."""
    if not row:
        return True
    raw = row.get("updated_at")
    if raw:
        try:
            created = raw if isinstance(raw, datetime) else datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            if created.date() != date.today():
                return True
        except (ValueError, TypeError):
            pass
    return row.get("holdings_hash") != current_hash
