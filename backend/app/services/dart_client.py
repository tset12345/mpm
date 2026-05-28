"""
금융감독원 Open DART API 클라이언트.

- 종목코드(6자리) → DART 고유번호(8자리) 변환 (XML/Zip 최초 1회 다운로드 + 메모리 캐싱)
- 최근 3개년 재무제표(연결우선·별도 폴백) 수집
- 최근 3개년 배당 정보 수집
- 반환: pandas DataFrame (문자열 → float 정제 포함)
"""

import asyncio
import io
import logging
import re
import xml.etree.ElementTree as ET
import zipfile
from datetime import date
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

DART_BASE = "https://opendart.fss.or.kr/api"
REPRT_CODE_ANNUAL = "11011"   # 사업보고서

# ── 메모리 캐시 ───────────────────────────────────────────────────────────────
_corp_code_map: dict[str, str] = {}   # stock_code(6자리) → corp_code(8자리)
_corp_code_loaded = False
_corp_code_lock = asyncio.Lock()


# ── 내부 유틸 ─────────────────────────────────────────────────────────────────

def _clean_number(value) -> Optional[float]:
    """쉼표·공백 등을 제거한 뒤 float으로 변환한다. 실패 시 None."""
    if value is None:
        return None
    cleaned = re.sub(r"[,\s]", "", str(value))
    try:
        return float(cleaned)
    except ValueError:
        return None


async def _ensure_corp_codes() -> None:
    """DART 기업코드 ZIP을 최초 1회 다운로드하고 메모리에 캐싱한다."""
    global _corp_code_loaded
    async with _corp_code_lock:
        if _corp_code_loaded:
            return

        if not settings.dart_api_key:
            logger.warning("DART_API_KEY 환경변수가 설정되지 않았습니다. DART 기능을 사용할 수 없습니다.")
            _corp_code_loaded = True
            return

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"{DART_BASE}/corpCode.xml",
                    params={"crtfc_key": settings.dart_api_key},
                )
                resp.raise_for_status()
        except Exception as e:
            logger.error(f"DART 기업코드 ZIP 다운로드 실패: {e}")
            _corp_code_loaded = True
            return

        try:
            with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                xml_bytes = zf.read("CORPCODE.xml")
            root = ET.fromstring(xml_bytes)
            for item in root.findall("list"):
                sc = (item.findtext("stock_code") or "").strip()
                cc = (item.findtext("corp_code") or "").strip()
                if sc and len(sc) == 6 and cc:
                    _corp_code_map[sc] = cc
            logger.info(f"DART 기업코드 캐시 완료: {len(_corp_code_map):,}개 종목")
        except Exception as e:
            logger.error(f"DART 기업코드 파싱 오류: {e}")
        finally:
            _corp_code_loaded = True


# ── 공개 함수 ─────────────────────────────────────────────────────────────────

async def get_corp_code(stock_code: str) -> Optional[str]:
    """6자리 종목코드를 DART 8자리 고유번호로 변환한다."""
    await _ensure_corp_codes()
    return _corp_code_map.get(stock_code.zfill(6))


async def fetch_financial_statements(corp_code: str, years: list[int]) -> pd.DataFrame:
    """
    지정 연도의 단일회사 주요계정(연결우선, 없으면 별도)을 수집한다.

    Returns DataFrame:
        columns: year, sj_div, account_nm, amount(float)
    """
    import pandas as pd
    rows: list[dict] = []

    async with httpx.AsyncClient(timeout=20.0) as client:
        for year in years:
            items: list[dict] = []
            for fs_div in ("CFS", "OFS"):   # 연결 → 별도 순으로 시도
                try:
                    resp = await client.get(
                        f"{DART_BASE}/fnlttSinglAcntAll.json",
                        params={
                            "crtfc_key": settings.dart_api_key,
                            "corp_code": corp_code,
                            "bsns_year": str(year),
                            "reprt_code": REPRT_CODE_ANNUAL,
                            "fs_div": fs_div,
                        },
                    )
                    body = resp.json()
                    if body.get("status") == "000" and body.get("list"):
                        items = body["list"]
                        break
                except Exception as e:
                    logger.debug(f"DART fnlttSinglAcntAll {year}/{fs_div} 오류: {e}")

            for item in items:
                rows.append({
                    "year": year,
                    "sj_div": item.get("sj_div", ""),
                    "account_nm": (item.get("account_nm") or "").strip(),
                    "amount": _clean_number(item.get("thstrm_amount")),
                })

    if not rows:
        return pd.DataFrame(columns=["year", "sj_div", "account_nm", "amount"])

    return pd.DataFrame(rows)


async def fetch_dividend_info(corp_code: str, years: list[int]) -> pd.DataFrame:
    """
    지정 연도의 배당에 관한 사항(주당배당금·배당성향·배당수익률)을 수집한다.

    Returns DataFrame:
        columns: year, dps(float), payout_ratio(float), dividend_yield(float)
    """
    import pandas as pd
    records: list[dict] = []

    async with httpx.AsyncClient(timeout=20.0) as client:
        for year in years:
            row: dict = {"year": year, "dps": None, "payout_ratio": None, "dividend_yield": None}
            try:
                resp = await client.get(
                    f"{DART_BASE}/alotMatter.json",
                    params={
                        "crtfc_key": settings.dart_api_key,
                        "corp_code": corp_code,
                        "bsns_year": str(year),
                        "reprt_code": REPRT_CODE_ANNUAL,
                    },
                )
                body = resp.json()
                for item in body.get("list", []):
                    se = (item.get("se") or "").strip()
                    val = _clean_number(item.get("thstrm"))
                    if val is None:
                        continue
                    if "주당 현금배당금" in se or "주당배당금" in se:
                        row["dps"] = val
                    elif "현금배당성향" in se or "배당성향" in se:
                        row["payout_ratio"] = val
                    elif "현금배당수익률" in se or "배당수익률" in se:
                        row["dividend_yield"] = val
            except Exception as e:
                logger.debug(f"DART alotMatter {year} 오류: {e}")
            records.append(row)

    if not records:
        return pd.DataFrame(columns=["year", "dps", "payout_ratio", "dividend_yield"])

    return pd.DataFrame(records)


async def collect_dart_data(stock_code: str, n_years: int = 3) -> dict:
    """
    종목코드로 DART 재무·배당 데이터를 일괄 수집하여 반환한다.

    Returns:
        {
          "corp_code": str | None,
          "financials": pd.DataFrame,   # (year, sj_div, account_nm, amount)
          "dividends":  pd.DataFrame,   # (year, dps, payout_ratio, dividend_yield)
          "error": str | None,
        }
    """
    import pandas as pd
    corp_code = await get_corp_code(stock_code)
    if not corp_code:
        return {
            "corp_code": None,
            "financials": pd.DataFrame(),
            "dividends": pd.DataFrame(),
            "error": f"종목코드 {stock_code}의 DART 기업코드를 찾을 수 없습니다.",
        }

    # 가장 최근 확정 사업보고서: 당해 연도 미확정이므로 전년 기준
    current_year = date.today().year
    target_years = list(range(current_year - n_years, current_year))  # e.g. [2022,2023,2024]

    fin_df, div_df = await asyncio.gather(
        fetch_financial_statements(corp_code, target_years),
        fetch_dividend_info(corp_code, target_years),
    )

    return {
        "corp_code": corp_code,
        "financials": fin_df,
        "dividends": div_df,
        "error": None,
    }


def extract_key_financials(fin_df: pd.DataFrame, year: int) -> dict:
    """
    재무제표 DataFrame에서 특정 연도의 핵심 계정을 추출한다.

    Returns:
        {net_income, total_assets, total_liabilities, total_equity,
         operating_cf, capex}  (단위: 백만원, 없으면 None)
    """
    if fin_df.empty:
        return {k: None for k in ["net_income", "total_assets", "total_liabilities",
                                   "total_equity", "operating_cf", "capex"]}

    yr = fin_df[fin_df["year"] == year]
    if yr.empty:
        return {k: None for k in ["net_income", "total_assets", "total_liabilities",
                                   "total_equity", "operating_cf", "capex"]}

    def _get(sj_div: str, *name_patterns: str) -> Optional[float]:
        subset = yr[yr["sj_div"] == sj_div]
        for pat in name_patterns:
            matched = subset[subset["account_nm"].str.contains(pat, na=False)]
            if not matched.empty:
                return matched.iloc[0]["amount"]
        return None

    return {
        "net_income":        _get("IS",  "당기순이익"),
        "total_assets":      _get("BS",  "자산총계"),
        "total_liabilities": _get("BS",  "부채총계"),
        "total_equity":      _get("BS",  "자본총계"),
        "operating_cf":      _get("CF",  "영업활동"),
        "capex":             _get("CF",  "유형자산의취득", "유형자산 취득"),
    }
