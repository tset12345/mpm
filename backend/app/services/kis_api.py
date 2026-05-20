import json
import time
import httpx
from pathlib import Path
from app.core.config import settings

BASE_URL_MOCK = "https://openapivts.koreainvestment.com:29443"
BASE_URL_REAL = "https://openapi.koreainvestment.com:9443"

# 토큰을 파일에 캐싱 — uvicorn 재시작 시에도 유지
_TOKEN_CACHE_FILE = Path(__file__).parent.parent.parent / ".kis_token_cache.json"

class KISApiClient:
    def __init__(self):
        self.base_url = BASE_URL_MOCK if settings.kis_is_mock else BASE_URL_REAL
        self._access_token: str | None = None
        self._token_expires_at: float = 0.0
        self._load_token_cache()

    def _load_token_cache(self):
        try:
            if _TOKEN_CACHE_FILE.exists():
                data = json.loads(_TOKEN_CACHE_FILE.read_text())
                if data.get("base_url") == self.base_url and data.get("expires_at", 0) > time.time() + 300:
                    self._access_token = data["token"]
                    self._token_expires_at = data["expires_at"]
        except Exception:
            pass

    def _save_token_cache(self):
        try:
            _TOKEN_CACHE_FILE.write_text(json.dumps({
                "token": self._access_token,
                "expires_at": self._token_expires_at,
                "base_url": self.base_url,
            }))
        except Exception:
            pass

    async def _get_token(self) -> str:
        if self._access_token and time.time() < self._token_expires_at - 300:
            return self._access_token
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/oauth2/tokenP",
                json={
                    "grant_type": "client_credentials",
                    "appkey": settings.kis_app_key,
                    "appsecret": settings.kis_app_secret,
                },
            )
            resp.raise_for_status()
            body = resp.json()
            self._access_token = body["access_token"]
            # KIS 토큰 만료: 86400초 (1일)
            expires_in = int(body.get("expires_in", 86400))
            self._token_expires_at = time.time() + expires_in
            self._save_token_cache()
            return self._access_token

    async def get_stock_price(self, stock_code: str) -> dict:
        token = await self._get_token()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-price",
                params={"fid_cond_mrkt_div_code": "J", "fid_input_iscd": stock_code},
                headers={
                    "authorization": f"Bearer {token}",
                    "appkey": settings.kis_app_key,
                    "appsecret": settings.kis_app_secret,
                    "tr_id": "FHKST01010100",
                },
            )
            resp.raise_for_status()
            return resp.json()

    async def get_daily_ohlcv(self, stock_code: str, start_date: str, end_date: str) -> dict:
        token = await self._get_token()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice",
                params={
                    "fid_cond_mrkt_div_code": "J",
                    "fid_input_iscd": stock_code,
                    "fid_input_date_1": start_date,
                    "fid_input_date_2": end_date,
                    "fid_period_div_code": "D",
                    "fid_org_adj_prc": "0",
                },
                headers={
                    "authorization": f"Bearer {token}",
                    "appkey": settings.kis_app_key,
                    "appsecret": settings.kis_app_secret,
                    "tr_id": "FHKST03010100",
                },
            )
            resp.raise_for_status()
            return resp.json()

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
        token = await self._get_token()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/uapi/domestic-stock/v1/ranking/near-new-highlow",
                params=self._NEAR_HIGH_PARAMS,
                headers={
                    "authorization": f"Bearer {token}",
                    "appkey": settings.kis_app_key,
                    "appsecret": settings.kis_app_secret,
                    "tr_id": "FHPST01870000",
                    "custtype": "P",
                },
                timeout=10.0,
            )
            resp.raise_for_status()
            return resp.json()

    async def get_vi_triggered_stocks(self) -> dict:
        """변동성완화장치(VI) 발동 종목 조회 (FHPST01390000). 장 중에만 데이터 발생."""
        token = await self._get_token()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/uapi/domestic-stock/v1/quotations/inquire-vi-status",
                params=self._VI_PARAMS,
                headers={
                    "authorization": f"Bearer {token}",
                    "appkey": settings.kis_app_key,
                    "appsecret": settings.kis_app_secret,
                    "tr_id": "FHPST01390000",
                    "custtype": "P",
                },
                timeout=10.0,
            )
            resp.raise_for_status()
            return resp.json()

    async def get_institution_foreign_net_buy_ranking(self) -> dict:
        """기관·외국인 순매수 상위 종목 조회 (frgn_ntby_qty + orgn_ntby_qty 기준)"""
        token = await self._get_token()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/uapi/domestic-stock/v1/quotations/foreign-institution-total",
                params=self._NET_BUY_PARAMS,
                headers={
                    "authorization": f"Bearer {token}",
                    "appkey": settings.kis_app_key,
                    "appsecret": settings.kis_app_secret,
                    "tr_id": "FHPTJ04400000",
                    "custtype": "P",
                },
                timeout=10.0,
            )
            resp.raise_for_status()
            return resp.json()

    async def _rank_request(self, tr_id: str) -> dict:
        token = await self._get_token()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.base_url}/uapi/domestic-stock/v1/quotations/volume-rank",
                params=self._RANK_PARAMS,
                headers={
                    "authorization": f"Bearer {token}",
                    "appkey": settings.kis_app_key,
                    "appsecret": settings.kis_app_secret,
                    "tr_id": tr_id,
                    "custtype": "P",
                },
                timeout=10.0,
            )
            resp.raise_for_status()
            return resp.json()

kis_client = KISApiClient()
