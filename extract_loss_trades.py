#!/usr/bin/env python3
"""
가상거래 손실 데이터 추출 스크립트
목적: 종목 추천 알고리즘 개선을 위한 손실 거래 분석
출력: CSV (거래시간, 종목 정보, 가격 정보)
"""

import csv
import os
import sys
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

load_dotenv(Path(__file__).parent / "backend" / ".env")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("❌ SUPABASE_URL / SUPABASE_SERVICE_KEY 환경변수가 없습니다.")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

OUTPUT_FILE = Path(__file__).parent / f"virtual_loss_trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"


FIELDNAMES = [
    "계좌명",
    "매도일",
    "종목코드",
    "종목명",
    "매수가(추정)",
    "매도가",
    "수량",
    "매도금액",
    "손익금액(원)",
    "손익률(%)",
    "매도유형",
    "엔진",
    "매수점수",
    "매도점수",
    "매수일(추정)",
    "보유일수",
]

TRIGGER_LABEL = {
    "stop_loss":          "손절",
    "take_profit":        "익절",
    "sell_signal":        "매도신호",
    "manual":             "수동",
    "entry_low_breach":   "진입저점이탈",
    "time_limit_stop":    "보유기간초과",
    "algo_sell":          "알고리즘매도",
}


def main():
    print("📡 데이터 조회 중...")

    # 계좌 목록
    accounts = {
        a["id"]: a["name"]
        for a in supabase.table("virtual_accounts").select("id, name").execute().data
    }

    # 손실 매도 거래 (pnl < 0)
    loss_trades = (
        supabase.table("virtual_trades")
        .select("*")
        .eq("side", "sell")
        .lt("pnl", 0)
        .order("traded_at", desc=True)
        .execute()
        .data
    )

    if not loss_trades:
        print("ℹ️  손실 거래 데이터가 없습니다.")
        return

    # 매수 거래 (보유일수 계산용)
    buy_trades = (
        supabase.table("virtual_trades")
        .select("account_id, stock_code, traded_at")
        .eq("side", "buy")
        .execute()
        .data
    )
    # (account_id, stock_code) → 매수일 목록 (정렬)
    buy_map: dict[tuple, list[str]] = defaultdict(list)
    for bt in buy_trades:
        buy_map[(bt["account_id"], bt["stock_code"])].append(bt["traded_at"])
    for key in buy_map:
        buy_map[key].sort()

    rows = []
    for t in loss_trades:
        qty   = t["quantity"] or 1
        pnl   = t["pnl"] or 0
        avg_price = round(t["price"] - pnl / qty)

        # 이 매도일 이전의 가장 최근 매수일
        buys = buy_map.get((t["account_id"], t["stock_code"]), [])
        entry_date = next((bd for bd in reversed(buys) if bd <= t["traded_at"]), None)
        hold_days  = (
            (date.fromisoformat(t["traded_at"]) - date.fromisoformat(entry_date)).days
            if entry_date else ""
        )

        rows.append({
            "계좌명":       accounts.get(t["account_id"], t["account_id"]),
            "매도일":       t["traded_at"],
            "종목코드":     t["stock_code"],
            "종목명":       t["stock_name"],
            "매수가(추정)": avg_price,
            "매도가":       t["price"],
            "수량":         t["quantity"],
            "매도금액":     t["amount"],
            "손익금액(원)": t["pnl"],
            "손익률(%)":    t["pnl_rate"],
            "매도유형":     TRIGGER_LABEL.get(t["trigger_type"] or "", t["trigger_type"]),
            "엔진":         t["engine"],
            "매수점수":     t["tech_score"],
            "매도점수":     t["sell_score"],
            "매수일(추정)": entry_date or "",
            "보유일수":     hold_days,
        })

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    print(f"✅ 추출 완료: {OUTPUT_FILE.name}")
    print(f"   손실 거래: {len(rows)}건")

    # 간단한 요약 통계
    pnl_rates = [float(r["손익률(%)"]) for r in rows if r["손익률(%)"] is not None]
    pnls      = [int(r["손익금액(원)"]) for r in rows if r["손익금액(원)"] is not None]
    triggers: dict[str, int] = {}
    for r in rows:
        t = str(r["매도유형"])
        triggers[t] = triggers.get(t, 0) + 1

    print(f"\n📊 요약")
    print(f"   총 손실금액 : {sum(pnls):,}원")
    print(f"   평균 손익률 : {sum(pnl_rates)/len(pnl_rates):.2f}%")
    print(f"   최대 손실률 : {min(pnl_rates):.2f}%")
    print(f"\n   매도유형별 건수:")
    for k, v in sorted(triggers.items(), key=lambda x: -x[1]):
        print(f"     {k}: {v}건")


if __name__ == "__main__":
    main()
