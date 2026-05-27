import asyncio
import json
import logging
from collections import defaultdict
from datetime import timedelta, datetime, timezone

from app.core.timezone import today_kst

from app.services.kis_api import kis_client
from app.services.supabase_client import supabase
from app.services import technical
from app.services.ichimoku import calculate as ichimoku_calculate

logger = logging.getLogger(__name__)

# ── 상수 ──────────────────────────────────────────────────────────────────────
MEANINGFUL_SCORE_THRESHOLD = 20   # tech + fund 합산 최소 점수
MIN_PRICE = 1_000                  # 동전주 필터링 기준 (원)
TOP_N = 10                         # 최종 추천 종목 수
FUND_TARGET_PTS = 15               # AI 리포트 주요 종목 언급 점수
FUND_RELATED_PTS = 5               # AI 리포트 관련 종목 언급 점수
FUND_MAX = 30                      # 펀더멘털 점수 상한

FALLBACK_STOCKS = [
    ("005930", "삼성전자",  74200),
    ("000660", "SK하이닉스", 195000),
    ("035420", "NAVER",    185000),
    ("005380", "현대차",   215000),
    ("000270", "기아",      97000),
    ("068270", "셀트리온",  182000),
    ("051910", "LG화학",   285000),
    ("035720", "카카오",    38000),
    ("105560", "KB금융",    89000),
    ("055550", "신한지주",  55000),
]

_ETF_NAME_KEYWORDS = {
    "KODEX", "TIGER", "KINDEX", "KOSEF", "HANARO", "RISE", "ACE", "SOL",
    "TIMEFOLIO", "ARIRANG", "TREX", "PLUS", "레버리지", "인버스", "2X", "TOP10",
}


# ── 유틸 ──────────────────────────────────────────────────────────────────────

def _is_etf_or_etn(code: str, name: str = "") -> bool:
    if len(code) != 6 or not code.isdigit():
        return True
    return any(kw.upper() in name.upper() for kw in _ETF_NAME_KEYWORDS)


def _to_float(val, default: float = 0.0) -> float:
    try:
        return float(val or default)
    except (ValueError, TypeError):
        return default


def _to_int(val, default: int = 0) -> int:
    try:
        return int(val or default)
    except (ValueError, TypeError):
        return default


def _db_rows_to_ohlcv(db_rows: list[dict]) -> list[dict]:
    """stock_ohlcv DB 행 → technical.analyze() 입력 형식 (날짜 오름차순)."""
    return [
        {
            "stck_clpr": str(r["close_price"]),
            "stck_hgpr": str(r["high_price"]),
            "stck_lwpr": str(r["low_price"]),
            "acml_vol":  str(r["volume"]),
        }
        for r in sorted(db_rows, key=lambda r: r["trade_date"])
    ]


def _is_bearish_alignment(records: list[dict]) -> bool:
    """역배열 판별: MA5 < MA20 이면 True (탈락)."""
    closes = [float(r.get("stck_clpr") or 0) for r in records]
    if len(closes) < 20:
        return True
    ma5  = technical.sma(closes, 5)
    ma20 = technical.sma(closes, 20)
    if ma5 is None or ma20 is None:
        return True
    return ma5 < ma20


# ── OHLCV 캐시 보완 ────────────────────────────────────────────────────────────

async def _load_cached_ohlcv(codes: list[str], start_date_iso: str) -> dict[str, list[dict]]:
    """Supabase stock_ohlcv에서 캐싱된 OHLCV 조회."""
    result: dict[str, list[dict]] = {code: [] for code in codes}
    try:
        rows = (
            supabase.table("stock_ohlcv")
            .select("stock_code,trade_date,open_price,high_price,low_price,close_price,volume")
            .in_("stock_code", codes)
            .gte("trade_date", start_date_iso)
            .order("trade_date")
            .execute()
        )
        for row in (rows.data or []):
            result[row["stock_code"]].append(row)
    except Exception as e:
        logger.warning(f"OHLCV 캐시 조회 실패: {e}")
    return result


def _kis_records_to_db_rows(code: str, output2: list[dict]) -> list[dict]:
    """KIS output2 레코드 → stock_ohlcv DB 행 형식으로 변환."""
    rows = []
    for r in output2:
        d = r.get("stck_bsop_date", "")
        if not d:
            continue
        rows.append({
            "stock_code":  code,
            "trade_date":  f"{d[:4]}-{d[4:6]}-{d[6:8]}",
            "open_price":  _to_int(r.get("stck_oprc")),
            "high_price":  _to_int(r.get("stck_hgpr")),
            "low_price":   _to_int(r.get("stck_lwpr")),
            "close_price": _to_int(r.get("stck_clpr")),
            "volume":      _to_int(r.get("acml_vol")),
        })
    return rows


async def _fetch_ohlcv_range(
    sem: asyncio.Semaphore, code: str, start_kis: str, end_kis: str
) -> tuple[str, list[dict]]:
    """KIS에서 기간 OHLCV를 조회해 DB 행 형식으로 반환."""
    async with sem:
        try:
            data = await kis_client.get_daily_ohlcv(code, start_kis, end_kis)
            rows = _kis_records_to_db_rows(code, list(reversed(data.get("output2", []))))
            return code, rows
        except Exception as e:
            logger.debug(f"{code} OHLCV 조회 실패({start_kis}~{end_kis}): {e}")
        return code, []


# ── 펀더멘털 점수 ──────────────────────────────────────────────────────────────

def _load_fund_scores(codes: list[str]) -> dict[str, int]:
    """최근 7일 AI 리포트에서 종목별 긍정 점수 산출."""
    fund: dict[str, int] = {code: 0 for code in codes}
    since = (today_kst() - timedelta(days=7)).isoformat()
    try:
        rows = (
            supabase.table("reports")
            .select("target_stock_code,related_stock_codes")
            .gte("publish_date", since)
            .execute()
        )
        for r in (rows.data or []):
            tc = r.get("target_stock_code")
            if tc and tc in fund:
                fund[tc] = min(fund[tc] + FUND_TARGET_PTS, FUND_MAX)

            related = r.get("related_stock_codes") or []
            if isinstance(related, str):
                try:
                    related = json.loads(related)
                except Exception:
                    related = []
            for rc in (related if isinstance(related, list) else []):
                if rc in fund:
                    fund[rc] = min(fund[rc] + FUND_RELATED_PTS, FUND_MAX)
    except Exception as e:
        logger.warning(f"AI 리포트 점수 조회 실패: {e}")
    return fund


# ── 메인 ──────────────────────────────────────────────────────────────────────

async def update_recommendations() -> list[dict]:
    today         = today_kst()
    today_str     = today.isoformat()                        # YYYY-MM-DD
    today_kis     = today.strftime("%Y%m%d")                 # YYYYMMDD
    today_iso     = today_str                                # alias
    start_date_iso = (today - timedelta(days=130)).isoformat()

    # ── 1. 5개 조건 병렬 수집 → ETF·동전주 필터 → rank_map 구성 ────────────────
    # A: 거래대금  B: 기관·외인 순매수  C: 거래량  D: 신고가근접  E: VI발동
    rank_map:   dict[str, dict]     = {}
    source_map: dict[str, set[str]] = defaultdict(set)

    cond_results = await asyncio.gather(
        kis_client.get_trading_amount_ranking(),               # A
        kis_client.get_institution_foreign_net_buy_ranking(),  # B
        kis_client.get_volume_ranking(),                       # C
        kis_client.get_new_high_ranking(),                     # D
        kis_client.get_vi_triggered_stocks(),                  # E
        return_exceptions=True,
    )

    _COND_LABELS = [
        ("거래대금(A)",    "거래대금"),
        ("기관·외인(B)",   "기관외인"),
        ("거래량(C)",      "거래량"),
        ("신고가근접(D)",  "신고가"),
        ("VI발동(E)",      "VI발동"),
    ]

    for (log_label, src_label), cond_data in zip(_COND_LABELS, cond_results):
        if isinstance(cond_data, Exception):
            logger.warning(f"{log_label} 조회 실패: {cond_data}")
            continue
        if cond_data.get("rt_cd") != "0":
            logger.warning(f"{log_label} API 오류: {cond_data.get('msg1')}")
            continue
        added = 0
        for item in cond_data.get("output", []):
            code  = item.get("mksc_shrn_iscd") or item.get("stck_shrn_iscd", "")
            name  = item.get("hts_kor_isnm", "")
            price = _to_int(item.get("stck_prpr") or item.get("stck_clpr"))
            if not code:
                continue
            source_map[code].add(src_label)   # 중복이어도 source는 기록
            if code in rank_map:
                continue
            if not _is_etf_or_etn(code, name) and price >= MIN_PRICE:
                rank_map[code] = item
                added += 1
            if added >= 30:
                break
        logger.info(f"{log_label}: {added}개 신규 추가 (누적 {len(rank_map)}개)")

    if not rank_map:
        logger.warning("모든 수급 조건 실패, 폴백 사용")
        rows = _make_fallback_rows(today_str)
        _upsert_rows(rows)
        return rows

    codes = list(rank_map.keys())

    # ── 2. OHLCV: Supabase 캐시 로드 + KIS 병렬 보완 ────────────────────────
    cached = await _load_cached_ohlcv(codes, start_date_iso)

    # 캐시 데이터 부족(<20일): 전체 기간 KIS 조회
    # 캐시는 있으나 오늘 데이터 없음: 오늘 하루만 KIS 조회
    sem = asyncio.Semaphore(5)
    full_fetch  = [c for c in codes if len(cached[c]) < 20]
    today_fetch = [c for c in codes if len(cached[c]) >= 20
                   and not any(r["trade_date"] == today_iso for r in cached[c])]

    start_kis = (today - timedelta(days=130)).strftime("%Y%m%d")

    tasks = (
        [_fetch_ohlcv_range(sem, c, start_kis, today_kis) for c in full_fetch] +
        [_fetch_ohlcv_range(sem, c, today_kis, today_kis) for c in today_fetch]
    )
    if tasks:
        results = await asyncio.gather(*tasks)
        for code, rows in results:
            if rows:
                existing_dates = {r["trade_date"] for r in cached[code]}
                cached[code].extend(r for r in rows if r["trade_date"] not in existing_dates)
                cached[code].sort(key=lambda r: r["trade_date"])
        if full_fetch:
            logger.info(f"OHLCV 전체 조회(캐시 미비): {len(full_fetch)}개")

    # ── 3. 역배열 탈락 → 최대 30개 압축 ─────────────────────────────────────
    valid_codes: list[str] = []
    for code in codes:
        records = _db_rows_to_ohlcv(cached[code])
        if not _is_bearish_alignment(records):
            valid_codes.append(code)
        if len(valid_codes) >= 30:
            break
    logger.info(f"역배열 필터링: {len(codes)}개 → {len(valid_codes)}개")

    # ── 4. 기술적 점수 산출 (일목 구름대 포함) ──────────────────────────────
    def _analyze_with_ichimoku(code: str) -> dict:
        records = _db_rows_to_ohlcv(cached[code])
        highs  = [float(r["stck_hgpr"]) for r in records]
        lows   = [float(r["stck_lwpr"]) for r in records]
        closes = [float(r["stck_clpr"]) for r in records]
        try:
            cloud_position = ichimoku_calculate(highs, lows, closes).get("position", "unknown")
        except Exception:
            cloud_position = "unknown"
        return technical.analyze(records, cloud_position=cloud_position)

    tech_map: dict[str, dict] = {
        code: _analyze_with_ichimoku(code)
        for code in valid_codes
    }

    # ── 5. 펀더멘털 점수 (최근 7일 AI 리포트) ────────────────────────────────
    fund_map = _load_fund_scores(valid_codes)

    # ── 6. 합산 점수 → Top N 선정 ────────────────────────────────────────────
    scored = sorted(
        valid_codes,
        key=lambda c: tech_map[c]["score"] + fund_map[c],
        reverse=True,
    )
    top = [c for c in scored if (tech_map[c]["score"] + fund_map[c]) >= MEANINGFUL_SCORE_THRESHOLD][:TOP_N]
    logger.info(f"최종 추천: {len(top)}개 (임계값 {MEANINGFUL_SCORE_THRESHOLD}점 이상, Top {TOP_N})")

    # ── 7. 행 조립 ────────────────────────────────────────────────────────────
    rows: list[dict] = []
    for code in top:
        item         = rank_map[code]
        ta           = tech_map[code]
        fs           = fund_map[code]
        total        = ta["score"] + fs
        current_price = _to_int(item.get("stck_prpr") or item.get("stck_clpr"))
        change_rate  = _to_float(item.get("prdy_ctrt"))
        w52_hgpr     = _to_float(item.get("w52_hgpr") or 0)

        tags = list(ta["tags"])
        if change_rate >= 3.0:
            tags.append("등락률 급등")
        if w52_hgpr > 0 and current_price >= w52_hgpr * 0.95:
            tags.append("52주 신고가 근접")
        if fs > 0:
            tags.append("리포트 언급")

        rows.append({
            "date":              today_str,
            "stock_code":        code,
            "stock_name":        item.get("hts_kor_isnm", ""),
            "current_price":     current_price,
            "change_rate":       change_rate,
            "volume":            _to_int(item.get("acml_vol")),
            "tags":              tags,
            "tech_score":        ta["score"],
            "fund_score":        fs,
            "total_score":       total,
            "source_conditions": sorted(source_map.get(code, set())),
        })

    _upsert_rows(rows)
    return rows


# ── 저장 ──────────────────────────────────────────────────────────────────────

def _upsert_rows(rows: list[dict]) -> None:
    """누적 적재: 과거 추천 내역 보존, 같은 날짜·종목은 최신 데이터로 갱신.
    entry_price는 최초 생성 시점 가격을 보존한다."""
    if not rows:
        logger.warning("저장할 추천 종목 없음")
        return

    today_date = rows[0]["date"]
    # 오늘 이미 저장된 entry_price 조회 — 첫 생성 가격 보존
    existing_prices: dict[str, int] = {}
    try:
        existing = (
            supabase.table("stock_recommendations")
            .select("stock_code,entry_price")
            .eq("date", today_date)
            .execute()
        )
        for r in (existing.data or []):
            ep = r.get("entry_price")
            if ep:
                existing_prices[r["stock_code"]] = ep
    except Exception as e:
        logger.warning(f"기존 entry_price 조회 실패: {e}")

    now_kst = datetime.now(timezone(timedelta(hours=9))).isoformat()
    for row in rows:
        row["entry_price"] = existing_prices.get(row["stock_code"]) or row.get("current_price")
        row["updated_at"] = now_kst

    try:
        supabase.table("stock_recommendations").upsert(
            rows,
            on_conflict="stock_code,date",
        ).execute()
        logger.info(f"추천 종목 {len(rows)}개 누적 저장 완료")
    except Exception as e:
        logger.error(f"추천 종목 저장 실패: {e}")
        raise


def _make_fallback_rows(today_str: str) -> list[dict]:
    return [
        {
            "date": today_str, "stock_code": code, "stock_name": name,
            "current_price": price, "change_rate": 0.0, "volume": 0,
            "tags": ["폴백 데이터"], "tech_score": 0, "fund_score": 0, "total_score": 0,
        }
        for code, name, price in FALLBACK_STOCKS
    ]
