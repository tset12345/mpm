"""
섹터 주도주 실시간 산출 서비스.

KIS API(현재가 · 등락률 · 거래대금 · 시가총액) +
DB stock_ohlcv(이동평균 계산)를 이용하여
섹터별 종목을 100점 만점으로 채점하고 상위 3개를 반환한다.

점수 배분
  ① 거래대금 (30점) : 섹터 내 최대 거래대금 대비 비율
  ② 상승률   (30점) : 섹터 내 최대 등락률 대비 비율 (하락 시 0점)
  ③ 정배열   (20점) : 5MA > 20MA > 60MA 조건 충족 시 20점
  ④ 시가총액 (20점) : 500억 미만 Hard Filter → 제외, 이상이면 20점
"""

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone

from app.services.kis_api import kis_client
from app.services.supabase_client import supabase
from app.services import technical
from app.services.ichimoku import calculate as ichimoku_calculate

logger = logging.getLogger(__name__)

# 시가총액 하한 필터 (억원 단위)
MKTCAP_THRESHOLD = 500

# ── 섹터별 대표 종목 매핑 ────────────────────────────────────────────────────
SECTOR_STOCKS: dict[str, list[str]] = {
    "반도체(AI/HBM)": [
        "005930",  # 삼성전자
        "000660",  # SK하이닉스
        "042700",  # 한미반도체
        "058470",  # 리노공업
        "036830",  # 솔브레인
        "357780",  # 솔루스첨단소재
        "267260",  # HD현대일렉트릭
    ],
    "온디바이스 AI": [
        "005930",  # 삼성전자
        "000660",  # SK하이닉스
        "066570",  # LG전자
        "034730",  # SK스퀘어
        "006400",  # 삼성SDI
        "005380",  # 현대차
    ],
    "2차전지 소재·장비": [
        "373220",  # LG에너지솔루션
        "006400",  # 삼성SDI
        "096770",  # SK이노베이션
        "086520",  # 에코프로
        "247540",  # 에코프로비엠
        "003670",  # 포스코퓨처엠
        "357780",  # 솔루스첨단소재
        "014830",  # OCI
    ],
    "로봇·스마트팩토리": [
        "277810",  # 레인보우로보틱스
        "454910",  # 두산로보틱스
        "090850",  # LS일렉트릭
        "032940",  # 파크시스템스
        "012330",  # 현대모비스
        "267250",  # HD현대
    ],
    "우주항공·방산": [
        "012450",  # 한화에어로스페이스
        "079550",  # LIG넥스원
        "047810",  # 한국항공우주
        "064350",  # 현대로템
        "000880",  # 한화
        "272210",  # 한화시스템
    ],
    "자율주행·전장부품": [
        "012330",  # 현대모비스
        "204320",  # HL만도
        "307950",  # 현대오토에버
        "005380",  # 현대차
        "000270",  # 기아
        "064960",  # S&T모티브
    ],
    "바이오시밀러·신약": [
        "207940",  # 삼성바이오로직스
        "068270",  # 셀트리온
        "128940",  # 한미약품
        "000100",  # 유한양행
        "185750",  # 종근당
        "012330",  # (제외 용도 - 없으면 아래 추가)
        "091990",  # 셀트리온헬스케어
    ],
    "양자컴퓨터·원자력(SMR)": [
        "034020",  # 두산에너빌리티
        "082740",  # HD현대일렉트릭
        "051600",  # 한전기술
        "105840",  # 도화엔지니어링
        "009830",  # 한화솔루션
    ],
    "자동차 제조": [
        "005380",  # 현대차
        "000270",  # 기아
        "012330",  # 현대모비스
        "064960",  # S&T모티브
        "005389",  # 현대차2우B
    ],
    "조선·해양플랜트": [
        "009540",  # HD한국조선해양
        "329180",  # HD현대중공업
        "010140",  # 삼성중공업
        "042660",  # 한화오션
        "267250",  # HD현대
        "008350",  # 남선알미늄 (제외)
    ],
    "철강·비철금속": [
        "005490",  # POSCO홀딩스
        "010130",  # 고려아연
        "004020",  # 현대제철
        "103140",  # 풍산
        "001440",  # 대한전선
    ],
    "화학·정유": [
        "051910",  # LG화학
        "096770",  # SK이노베이션
        "078930",  # GS
        "010950",  # S-Oil
        "011170",  # 롯데케미칼
    ],
    "디스플레이·OLED": [
        "034220",  # LG디스플레이
        "006400",  # 삼성SDI
        "357780",  # 솔루스첨단소재
        "078340",  # 컴투스홀딩스 (제외)
        "183300",  # 코미코
        "036490",  # 씨씨에스
    ],
    "기계·건설장비": [
        "267250",  # HD현대
        "241560",  # 두산밥캣
        "042670",  # 두산인프라코어
        "082740",  # HD현대일렉트릭
        "012630",  # HDC
    ],
    "인터넷·엔터테인먼트": [
        "035720",  # 카카오
        "035420",  # NAVER
        "352820",  # 하이브
        "041510",  # SM엔터테인먼트
        "122870",  # YG PLUS
        "035900",  # JYP Ent.
    ],
    "게임·콘텐츠": [
        "251270",  # 넷마블
        "259960",  # 크래프톤
        "036570",  # 엔씨소프트
        "263750",  # 펄어비스
        "293490",  # 카카오게임즈
        "225570",  # 넥슨게임즈
    ],
    "금융(은행·보험·증권)": [
        "105560",  # KB금융
        "055550",  # 신한지주
        "086790",  # 하나금융지주
        "032830",  # 삼성생명
        "316140",  # 우리금융지주
        "071050",  # 한국금융지주
    ],
    "음식료": [
        "097950",  # CJ제일제당
        "271560",  # 오리온
        "004370",  # 농심
        "007310",  # 오뚜기
        "003230",  # 삼양식품
        "004990",  # 롯데지주
    ],
    "화장품·미용기기": [
        "090430",  # 아모레퍼시픽
        "051900",  # LG생활건강
        "192820",  # 코스맥스
        "214150",  # 클래시스
        "161890",  # 한국콜마
        "078520",  # 에이블씨엔씨
    ],
    "신재생 에너지": [
        "009830",  # 한화솔루션
        "010060",  # OCI홀딩스
        "011690",  # 코오롱인더
        "012450",  # 한화에어로스페이스
        "267250",  # HD현대
        "034020",  # 두산에너빌리티
    ],
}


# ── 내부 헬퍼 ─────────────────────────────────────────────────────────────────

# KIS API 동시 호출 제한 (과부하 방지)
_KIS_SEM = asyncio.Semaphore(5)


def _safe_float(val, default: float = 0.0) -> float:
    try:
        s = str(val).replace("+", "").replace(",", "").strip()
        return float(s) if s else default
    except (ValueError, TypeError):
        return default


def _calc_ma(closes: list[float], n: int) -> float | None:
    if len(closes) < n:
        return None
    return sum(closes[-n:]) / n


async def _fetch_stock_snapshot(stock_code: str) -> dict | None:
    """KIS API에서 현재가·등락률·거래대금·시가총액·거래량 조회."""
    async with _KIS_SEM:
        return await _fetch_stock_snapshot_inner(stock_code)


async def _fetch_stock_snapshot_inner(stock_code: str) -> dict | None:
    try:
        data = await kis_client.get_stock_price(stock_code)
        out = data.get("output", {})
        return {
            "stock_code": stock_code,
            "stock_name": out.get("hts_kor_isnm") or stock_code,
            "current_price": _safe_float(out.get("stck_prpr")),
            "change_rate": _safe_float(out.get("prdy_ctrt")),
            "transaction_amount": _safe_float(out.get("acml_tr_pbmn")),
            "market_cap": _safe_float(out.get("hts_avls")),  # 억원
            "volume": int(_safe_float(out.get("acml_vol"))),
        }
    except Exception as e:
        logger.warning(f"[sector_leader] KIS 조회 실패 {stock_code}: {type(e).__name__}: {e}")
        return None


# ── 공개 API ──────────────────────────────────────────────────────────────────

async def get_sector_leaders(sector: str, market_regime: str = "BULL") -> list[dict]:
    """
    섹터 내 종목을 채점하여 상위 3개를 반환한다.
    각 항목에 rank(1~3), score(0~100), score_detail, tags가 포함된다.
    """
    codes = SECTOR_STOCKS.get(sector, [])
    if not codes:
        return []

    # ── 1. KIS API 병렬 조회 ─────────────────────────────────────────────────
    raw_results = await asyncio.gather(
        *[_fetch_stock_snapshot(c) for c in codes],
        return_exceptions=True,
    )
    snapshot: dict[str, dict] = {}
    for r in raw_results:
        if isinstance(r, dict):
            snapshot[r["stock_code"]] = r

    # ── 2. stock_master에서 종목명 조회 ──────────────────────────────────────
    valid_codes = list(snapshot.keys())
    try:
        master_rows = (
            supabase.table("stock_master")
            .select("stock_code,stock_name,market")
            .in_("stock_code", valid_codes)
            .execute()
        ).data or []
        name_map   = {r["stock_code"]: r["stock_name"] for r in master_rows}
        market_map = {r["stock_code"]: r["market"]     for r in master_rows}
    except Exception as e:
        logger.warning(f"[sector_leader] stock_master 조회 실패: {e}")
        name_map   = {}
        market_map = {}

    for code, snap in snapshot.items():
        if code in name_map:
            snap["stock_name"] = name_map[code]
        snap["market"] = market_map.get(code)

    # ── 3. OHLCV DB 조회 (MA + 기술 분석용) ──────────────────────────────────
    start_iso = (date.today() - timedelta(days=130)).isoformat()
    try:
        rows = (
            supabase.table("stock_ohlcv")
            .select("stock_code,high_price,low_price,close_price,volume,trade_date")
            .in_("stock_code", valid_codes)
            .gte("trade_date", start_iso)
            .order("trade_date")
            .execute()
        ).data or []
    except Exception as e:
        logger.warning(f"[sector_leader] DB 조회 실패: {e}")
        rows = []

    ohlcv_by_code: dict[str, list[dict]] = {c: [] for c in valid_codes}
    for row in rows:
        code = row["stock_code"]
        if code in ohlcv_by_code:
            ohlcv_by_code[code].append(row)

    # ── 4. MA 계산, 정배열 판정, 기술 점수 산출 ──────────────────────────────
    for code, snap in snapshot.items():
        db_rows = ohlcv_by_code.get(code, [])
        closes  = [float(r["close_price"]) for r in db_rows if r.get("close_price")]

        ma5  = _calc_ma(closes, 5)
        ma20 = _calc_ma(closes, 20)
        ma60 = _calc_ma(closes, 60)
        snap["ma5"]  = ma5
        snap["ma20"] = ma20
        snap["ma60"] = ma60
        snap["ma_aligned"] = bool(
            ma5 is not None and ma20 is not None and ma60 is not None
            and ma5 > ma20 > ma60
        )

        # 기술 분석 점수 (추천 알고리즘과 동일)
        if len(db_rows) >= 30:
            records = [
                {
                    "stck_clpr": str(r["close_price"]),
                    "stck_hgpr": str(r["high_price"]),
                    "stck_lwpr": str(r["low_price"]),
                    "acml_vol":  str(r["volume"]),
                }
                for r in db_rows
            ]
            highs_list  = [float(r["stck_hgpr"]) for r in records]
            lows_list   = [float(r["stck_lwpr"]) for r in records]
            closes_list = [float(r["stck_clpr"]) for r in records]
            try:
                cloud_pos = ichimoku_calculate(highs_list, lows_list, closes_list).get("position", "unknown")
            except Exception:
                cloud_pos = "unknown"
            ta = technical.analyze(records, cloud_position=cloud_pos, market_regime=market_regime)
        else:
            ta = {"score": 0, "engine_a_score": 0, "engine_b_score": 0, "tags": []}

        snap["tech_score"]    = ta["score"]
        snap["engine_a_score"] = ta.get("engine_a_score", 0)
        snap["engine_b_score"] = ta.get("engine_b_score", 0)
        snap["tech_tags"]     = list(ta.get("tags", []))

    # ── 5. 시가총액 Hard Filter ───────────────────────────────────────────────
    valid = [s for s in snapshot.values() if s["market_cap"] >= MKTCAP_THRESHOLD]
    if not valid:
        return []

    # ── 6. 섹터 내 최댓값 ─────────────────────────────────────────────────────
    max_amount = max((s["transaction_amount"] for s in valid), default=1) or 1
    max_rate   = max((s["change_rate"]        for s in valid), default=0)

    # ── 7. 점수 산출 ──────────────────────────────────────────────────────────
    for s in valid:
        amount_score = round((s["transaction_amount"] / max_amount) * 30)
        if max_rate > 0:
            rate_score = round(max(0.0, s["change_rate"] / max_rate) * 30)
        else:
            rate_score = 0
        ma_score     = 20 if s["ma_aligned"] else 0
        mktcap_score = 20  # 필터 통과 = 20점

        total = amount_score + rate_score + ma_score + mktcap_score
        s["score"] = total
        s["score_detail"] = {
            "amount":     amount_score,
            "rate":       rate_score,
            "ma_aligned": ma_score,
            "mktcap":     mktcap_score,
        }

        tags: list[str] = []
        if amount_score >= 20:
            tags.append("거래대금")
        if rate_score >= 20:
            tags.append("상승률")
        if s["ma_aligned"]:
            tags.append("정배열")
        s["tags"] = tags

    # ── 8. 정렬 후 상위 3개 반환 ─────────────────────────────────────────────
    ranked = sorted(valid, key=lambda x: x["score"], reverse=True)[:3]
    for i, s in enumerate(ranked, start=1):
        s["rank"] = i
    return ranked


# ── 캐시 레이어 ───────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _save_to_cache(sector: str, leaders: list[dict]) -> str:
    now = _now_iso()
    try:
        supabase.table("sector_leaders").upsert({
            "sector": sector,
            "data": leaders,
            "updated_at": now,
        }).execute()
    except Exception as e:
        logger.warning(f"[sector_leader] 캐시 저장 실패 {sector}: {e}")
    return now


async def get_sector_leaders_cached(sector: str, force: bool = False) -> tuple[list[dict], str | None]:
    """DB 캐시 우선 반환. force=True 이면 KIS 재조회 후 저장."""
    if not force:
        try:
            row = (
                supabase.table("sector_leaders")
                .select("data,updated_at")
                .eq("sector", sector)
                .limit(1)
                .execute()
            ).data
            if row:
                return row[0]["data"], row[0]["updated_at"]
        except Exception as e:
            logger.warning(f"[sector_leader] 캐시 조회 실패 {sector}: {e}")

    leaders = await get_sector_leaders(sector)
    if leaders:
        updated_at = _save_to_cache(sector, leaders)
    else:
        updated_at = None
    return leaders, updated_at


async def get_all_sectors_cached() -> list[dict]:
    """모든 섹터의 캐시 데이터를 한 번에 반환 (DB 단일 조회)."""
    try:
        rows = (
            supabase.table("sector_leaders")
            .select("sector,data,updated_at")
            .execute()
        ).data or []
        row_map = {r["sector"]: r for r in rows}
    except Exception as e:
        logger.warning(f"[sector_leader] 전체 캐시 조회 실패: {e}")
        row_map = {}

    return [
        {
            "sector": s,
            "leaders": row_map[s]["data"] if s in row_map else [],
            "updated_at": row_map[s]["updated_at"] if s in row_map else None,
        }
        for s in SECTOR_STOCKS
    ]


async def refresh_all_sectors() -> None:
    """모든 섹터를 순차 갱신하여 DB에 저장 (스케줄러 전용)."""
    from app.services.recommendations import _fetch_market_regime
    logger.info("[sector_leader] 전체 섹터 갱신 시작")
    market_regime = await _fetch_market_regime()
    logger.info(f"[sector_leader] 시장 레짐: {market_regime}")
    for sector in SECTOR_STOCKS:
        try:
            leaders = await get_sector_leaders(sector, market_regime=market_regime)
            if leaders:
                _save_to_cache(sector, leaders)
                logger.info(f"[sector_leader] 갱신 완료: {sector} ({len(leaders)}개)")
            else:
                logger.warning(f"[sector_leader] 빈 결과 — 캐시 유지: {sector}")
        except Exception as e:
            logger.error(f"[sector_leader] 갱신 실패 {sector}: {e}")
    logger.info("[sector_leader] 전체 섹터 갱신 완료")
