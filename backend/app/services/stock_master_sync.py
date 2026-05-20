import logging
from html.parser import HTMLParser

import httpx
from app.services.supabase_client import supabase

logger = logging.getLogger(__name__)

_KIND_URL = "https://kind.krx.co.kr/corpgeneral/corpList.do"
_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
_MARKETS = [("stockMkt", "KOSPI"), ("kosdaqMkt", "KOSDAQ")]


class _TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self._in_td = False
        self.rows: list[list[str]] = []
        self._row: list[str] = []
        self._cell = ""

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._row = []
        elif tag == "td":
            self._in_td = True
            self._cell = ""

    def handle_endtag(self, tag):
        if tag == "td":
            self._in_td = False
            self._row.append(self._cell.strip())
        elif tag == "tr" and self._row:
            self.rows.append(self._row)

    def handle_data(self, data):
        if self._in_td:
            self._cell += data


def _parse_listings(html: str, market: str) -> list[dict]:
    parser = _TableParser()
    parser.feed(html)
    records = []
    for row in parser.rows:
        if len(row) < 3:
            continue
        name = row[0].strip()
        code = row[2].strip()
        if code and name and code.isdigit() and len(code) == 6:
            records.append({"stock_code": code, "stock_name": name, "market": market})
    return records


async def sync_stock_master() -> dict:
    """kind.krx.co.kr에서 KOSPI·KOSDAQ 상장 종목을 받아 stock_master 테이블에 upsert."""
    records: list[dict] = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        for mkt_param, market in _MARKETS:
            try:
                resp = await client.get(
                    _KIND_URL,
                    params={"method": "download", "searchType": "13", "marketType": mkt_param},
                    headers=_HEADERS,
                    follow_redirects=True,
                )
                resp.raise_for_status()
                html = resp.content.decode("euc-kr", errors="replace")
                parsed = _parse_listings(html, market)
                records.extend(parsed)
                logger.info(f"{market} {len(parsed)}건 수집")
            except Exception as e:
                logger.error(f"{market} 수집 실패: {e}")

    if not records:
        return {"total": 0}

    chunk_size = 500
    for i in range(0, len(records), chunk_size):
        supabase.table("stock_master").upsert(
            records[i : i + chunk_size], on_conflict="stock_code"
        ).execute()

    return {"total": len(records)}
