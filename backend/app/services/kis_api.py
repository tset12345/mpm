import asyncio
import logging
import json
import time
import httpx
from pathlib import Path
from app.core.config import settings

logger = logging.getLogger(__name__)

BASE_URL_MOCK = "https://openapivts.koreainvestment.com:29443"
BASE_URL_REAL = "https://openapi.koreainvestment.com:9443"

# 토큰을 파일에 캐싱 — uvicorn 재시작 시에도 유지
_TOKEN_CACHE_FILE = Path(__file__).parent.parent.parent / ".kis_token_cache.json"

_RETRY_STATUS = {429, 500, 502, 503, 504}
_MAX_ATTEMPTS = 3
_BACKOFF_SEC = 0.4


class _RateLimiter:
    """초당 요청 수를 일정 간격으로 분산한다 (KIS 실전 20건/초, 모의 2건/초 제한 대비)."""

    def __init__(self, rate: float):
        self.interval = 1.0 / rate
        self._next = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            start = max(now, self._next)
            self._next = start + self.interval
        delay = start - now
        if delay > 0:
            await asyncio.sleep(delay)


class KISApiClient:
    def __init__(self):
        self.base_url = BASE_URL_MOCK if settings.kis_is_mock else BASE_URL_REAL
        self._access_token: str | None = None
        self._token_expires_at: float = 0.0
        self._http: httpx.AsyncClient | None = None  # 공유 클라이언트 — 매 호출마다 생성 금지
        rate = settings.kis_max_rps or (2.0 if settings.kis_is_mock else 15.0)
        self._limiter = _RateLimiter(rate)
        self._slots = asyncio.Semaphore(settings.kis_max_concurrency)
        self._load_token_cache()

    def _get_http(self) -> httpx.AsyncClient:
        """공유 AsyncClient 반환. 닫혀 있으면 새로 생성."""
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(timeout=15.0)
        return self._http

    async def aclose(self):
        """앱 종료 시 호출 — 공유 클라이언트와 연결을 정상 종료."""
        if self._http and not self._http.is_closed:
            await self._http.aclose()
            self._http = None

    def _load_token_cache(self):
        try:
            if _TOKEN_CACHE_FILE.exists():
                data = json.loads(_TOKEN_CACHE_FILE.read_text())
                if data.get("base_url") == self.base_url and data.get("expires_at", 0) > time.time() + 300:
                    self._access_token = data["token"]
                    self._token_expires_at = data["expires_at"]
        except Exception:
            logger.warning("_load_token_cache: 예외 무시하고 계속 진행", exc_info=True)

    def _save_token_cache(self):
        try:
            _TOKEN_CACHE_FILE.write_text(json.dumps({
                "token": self._access_token,
                "expires_at": self._token_expires_at,
                "base_url": self.base_url,
            }))
        except Exception:
            logger.warning("_save_token_cache: 예외 무시하고 계속 진행", exc_info=True)

    async def _get_token(self) -> str:
        if self._access_token and time.time() < self._token_expires_at - 300:
            return self._access_token
        client = self._get_http()
        resp = await client.post(
            f"{self.base_url}/oauth2/tokenP",
            json={
                "grant_type": "client_credentials",
                "appkey": settings.kis_app_key,
                "appsecret": settings.kis_app_secret,
            },
            timeout=15.0,
        )
        resp.raise_for_status()
        body = resp.json()
        self._access_token = body["access_token"]
        # KIS 토큰 만료: 86400초 (1일)
        expires_in = int(body.get("expires_in", 86400))
        self._token_expires_at = time.time() + expires_in
        self._save_token_cache()
        return self._access_token

    async def _get(self, path: str, tr_id: str, params: dict, custtype: str | None = None) -> dict:
        """모든 KIS 조회의 단일 진입점.

        전역 속도·동시성 제한을 적용하고, 일시 오류(429/5xx/네트워크)는 재시도하며,
        401이면 토큰을 새로 받아 한 번 더 시도한다.
        """
        refreshed = False
        last_exc: Exception | None = None
        for attempt in range(1, _MAX_ATTEMPTS + 1):
            token = await self._get_token()
            headers = {
                "authorization": f"Bearer {token}",
                "appkey": settings.kis_app_key,
                "appsecret": settings.kis_app_secret,
                "tr_id": tr_id,
            }
            if custtype:
                headers["custtype"] = custtype
            try:
                async with self._slots:
                    await self._limiter.acquire()
                    resp = await self._get_http().get(
                        f"{self.base_url}{path}", params=params, headers=headers, timeout=10.0,
                    )
            except httpx.TransportError as e:
                last_exc = e
                logger.warning("KIS 네트워크 오류 %s (%d/%d): %s", tr_id, attempt, _MAX_ATTEMPTS, e)
            else:
                if resp.status_code == 401 and not refreshed:
                    refreshed = True
                    self._access_token = None
                    self._token_expires_at = 0.0
                    logger.warning("KIS 401 — 토큰을 재발급해 재시도: %s", tr_id)
                    continue
                if resp.status_code in _RETRY_STATUS and attempt < _MAX_ATTEMPTS:
                    last_exc = httpx.HTTPStatusError(
                        f"HTTP {resp.status_code}", request=resp.request, response=resp)
                    logger.warning("KIS HTTP %s %s (%d/%d)", resp.status_code, tr_id, attempt, _MAX_ATTEMPTS)
                else:
                    resp.raise_for_status()
                    return resp.json()
            if attempt < _MAX_ATTEMPTS:
                await asyncio.sleep(_BACKOFF_SEC * attempt)
        raise last_exc if last_exc else RuntimeError("KIS 요청 실패")

    async def get_stock_price(self, stock_code: str) -> dict:
        return await self._get(
            "/uapi/domestic-stock/v1/quotations/inquire-price", "FHKST01010100",
            {"fid_cond_mrkt_div_code": "J", "fid_input_iscd": stock_code},
        )

    async def get_daily_ohlcv(self, stock_code: str, start_date: str, end_date: str) -> dict:
        return await self._get(
            "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice", "FHKST03010100",
            {
                "fid_cond_mrkt_div_code": "J",
                "fid_input_iscd": stock_code,
                "fid_input_date_1": start_date,
                "fid_input_date_2": end_date,
                "fid_period_div_code": "D",
                "fid_org_adj_prc": "0",
            },
        )

    async def get_index_chart(self, market_code: str, start_date: str, end_date: str, period: str = "D") -> dict:
        """국내 지수 기간별 시세 (KOSPI: 0001, KOSDAQ: 1001), period: D/W/M"""
        return await self._get(
            "/uapi/domestic-stock/v1/quotations/inquire-index-daily-price", "FHKUP03500100",
            {
                "fid_cond_mrkt_div_code": "U",
                "fid_input_iscd": market_code,
                "fid_input_date_1": start_date,
                "fid_input_date_2": end_date,
                "fid_period_div_code": period,
            },
            custtype="P",
        )

    _RANK_PARAMS = {
        "fid_cond_mrkt_div_code": "J",
        "fid_cond_scr_div_code": "20171",
        "fid_input_iscd": "0000",
        "fid_div_cls_code": "0",
        "fid_blng_cls_code": "0",
        "fid_trgt_cls_code": "111111111",
        "fid_trgt_exls_cls_code": "000000",
        "fid_input_price_1": "",
        "fid_input_price_2": "",
        "fid_vol_cnt": "",
        "fid_input_date_1": "",
        "fid_rank_sort_cls_code": "0",
        "fid_input_cnt_1": "0",
        "fid_prc_cls_code": "0",
        "fid_rsfl_rate1": "0",
        "fid_rsfl_rate2": "0",
        "fid_input_option": "",
        "fid_rsfl_yn": "",
        "fid_mkt_cls_code": "",
    }

    async def get_volume_ranking(self) -> dict:
        """거래량 순위 상위 종목 조회"""
        return await self._rank_request("FHPST01700000")

    async def get_trading_amount_ranking(self) -> dict:
        """거래대금 순위 상위 종목 조회"""
        return await self._rank_request("FHPST01710000")

    _NET_BUY_PARAMS = {
        "fid_cond_mrkt_div_code": "J",
        "fid_cond_scr_div_code": "20174",
        "fid_input_iscd": "0000",
        "fid_div_cls_code": "0",
        "fid_etc_cls_code": "0",        # 0=전체, 1=외국인, 2=기관
        "fid_rank_sort_cls_code": "0",  # 0=순매수량 내림차순
        "fid_trgt_cls_code": "111111111",
        "fid_trgt_exls_cls_code": "000000",
        "fid_input_price_1": "",
        "fid_input_price_2": "",
        "fid_vol_cnt": "",
        "fid_input_date_1": "",
        "fid_input_cnt_1": "0",
        "fid_prc_cls_code": "0",
    }

    _NEAR_HIGH_PARAMS = {
        "fid_cond_mrkt_div_code": "J",
        "fid_cond_scr_div_code": "20171",
        "fid_input_iscd": "0000",
        "fid_div_cls_code": "1",        # 1=신고가근접
        "fid_blng_cls_code": "0",
        "fid_trgt_cls_code": "111111111",
        "fid_trgt_exls_cls_code": "000000",
        "fid_input_price_1": "",
        "fid_input_price_2": "",
        "fid_vol_cnt": "",
        "fid_input_date_1": "",
        "fid_rank_sort_cls_code": "0",
        "fid_input_cnt_1": "0",
        "fid_input_cnt_2": "0",
        "fid_prc_cls_code": "0",
        "fid_aply_rang_prc_1": "0",
        "fid_aply_rang_prc_2": "0",
        "fid_aply_rang_vol": "0",
    }

    _VI_PARAMS = {
        "fid_cond_mrkt_div_code": "J",
        "fid_cond_scr_div_code": "20171",
        "fid_mrkt_cls_code": "0",
        "fid_input_iscd": "0000",
        "fid_div_cls_code": "0",
        "fid_trgt_cls_code": "111111111",
        "fid_trgt_exls_cls_code": "000000",
        "fid_input_price_1": "",
        "fid_input_price_2": "",
        "fid_vol_cnt": "",
        "fid_rank_sort_cls_code": "0",
        "fid_input_date_1": "",
    }

    async def get_new_high_ranking(self) -> dict:
        """신/신고가 근접 상위 종목 조회 (FHPST01870000)"""
        return await self._highlow_request("1")

    async def get_52week_high_low(self, div_cls: str) -> dict:
        """52주 신고가(div_cls='3') / 신저가(div_cls='4') 조회"""
        return await self._highlow_request(div_cls)

    async def _highlow_request(self, div_cls: str) -> dict:
        return await self._get(
            "/uapi/domestic-stock/v1/ranking/near-new-highlow", "FHPST01870000",
            {**self._NEAR_HIGH_PARAMS, "fid_div_cls_code": div_cls}, custtype="P",
        )

    async def get_vi_triggered_stocks(self) -> dict:
        """변동성완화장치(VI) 발동 종목 조회 (FHPST01390000). 장 중에만 데이터 발생."""
        return await self._get(
            "/uapi/domestic-stock/v1/quotations/inquire-vi-status", "FHPST01390000",
            self._VI_PARAMS, custtype="P",
        )

    async def get_institution_foreign_net_buy_ranking(self) -> dict:
        """기관·외국인 합산 순매수 상위 종목 (investor-trend용)"""
        return await self._net_buy_request("0")

    async def get_foreign_net_buy_ranking(self) -> dict:
        """외국인 순매수 상위 종목 (fid_etc_cls_code=1)"""
        return await self._net_buy_request("1")

    async def get_institution_net_buy_ranking(self) -> dict:
        """기관 순매수 상위 종목 (fid_etc_cls_code=2)"""
        return await self._net_buy_request("2")

    async def _net_buy_request(self, etc_cls: str) -> dict:
        return await self._get(
            "/uapi/domestic-stock/v1/quotations/foreign-institution-total", "FHPTJ04400000",
            {**self._NET_BUY_PARAMS, "fid_etc_cls_code": etc_cls}, custtype="P",
        )

    async def _rank_request(self, tr_id: str) -> dict:
        return await self._get(
            "/uapi/domestic-stock/v1/quotations/volume-rank", tr_id,
            self._RANK_PARAMS, custtype="P",
        )


kis_client = KISApiClient()
