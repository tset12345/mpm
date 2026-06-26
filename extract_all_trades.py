#!/usr/bin/env python3
"""가상거래 전체 거래내역 추출 스크립트"""

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

OUTPUT_FILE = Path(__file__).parent / f"virtual_all_trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

FIELDNAMES = [
    "계좌명", "거래일", "구분", "종목코드", "종목명",
    "체결가", "수량", "거래금액",
    "매수가(추정)", "손익금액(원)", "손익률(%)",
    "거래유형", "엔진", "매수점수", "매도점수",
    "매수일(추정)", "보유일수",
]

TRIGGER_LABEL = {
    "stop_loss":          "손절",
    "take_profit":        "익절",
    "sell_signal":        "매도신호",
    "manual":             "수동",
    "entry_low_breach":   "진입저점이탈",
    "time_limit_stop":    "보유기간초과",
    "algo_sell":          "알고리즘매도",
    "algo_buy":           "알고리즘매수",
    "atr_hard_stop":      "ATR하드스탑",
    "atr_trailing_stop":  "ATR트레일링",
    "rsi_exhaustion":     "RSI모멘텀소멸",
    "ma20_half_exit":     "MA20분할익절",
    "target_reached":     "목표도달",
}


def main():
    print("📡 데이터 조회 중...")

    accounts = {
        a["id"]: a["name"]
        for a in supabase.table("virtual_accounts").select("id, name").execute().data
    }

    all_trades = (
        supabase.table("virtual_trades")
        .select("*")
        .order("traded_at", desc=True)
        .order("created_at", desc=True)
        .execute()
        .data
    )

    if not all_trades:
        print("ℹ️  거래 데이터가 없습니다.")
        return

    # 매수 거래 맵 (보유일수 계산용)
    buy_trades = [t for t in all_trades if t["side"] == "buy"]
    buy_map: dict[tuple, list[str]] = defaultdict(list)
    for bt in buy_trades:
        buy_map[(bt["account_id"], bt["stock_code"])].append(bt["traded_at"])
    for key in buy_map:
        buy_map[key].sort()

    rows = []
    for t in all_trades:
        is_sell = t["side"] == "sell"
        qty = t["quantity"] or 1
        pnl = t.get("pnl")
        price = t["price"] or 0

        # 매수가 추정 (매도 시 pnl로 역산, 매수 시 체결가 = 매수가)
        if is_sell and pnl is not None:
            avg_price = round(price - pnl / qty)
        elif not is_sell:
            avg_price = price
        else:
            avg_price = ""

        # 매수일(추정): 이 거래일 이전의 가장 최근 매수일
        buys = buy_map.get((t["account_id"], t["stock_code"]), [])
        if is_sell:
            entry_date = next((bd for bd in reversed(buys) if bd <= t["traded_at"]), None)
        else:
            entry_date = ""

        hold_days = ""
        if is_sell and entry_date:
            try:
                hold_days = (date.fromisoformat(t["traded_at"]) - date.fromisoformat(entry_date)).days
            except (ValueError, TypeError):
                hold_days = ""

        rows.append({
            "계좌명":       accounts.get(t["account_id"], t["account_id"]),
            "거래일":       t["traded_at"],
            "구분":         "매도" if is_sell else "매수",
            "종목코드":     t["stock_code"],
            "종목명":       t["stock_name"],
            "체결가":       price,
            "수량":         t["quantity"],
            "거래금액":     t["amount"],
            "매수가(추정)": avg_price,
            "손익금액(원)": pnl if is_sell else "",
            "손익률(%)":    t.get("pnl_rate") if is_sell else "",
            "거래유형":     TRIGGER_LABEL.get(t.get("trigger_type") or "", t.get("trigger_type") or ""),
            "엔진":         t.get("engine") or "",
            "매수점수":     t.get("tech_score") or "",
            "매도점수":     t.get("sell_score") or "",
            "매수일(추정)": entry_date if is_sell else "",
            "보유일수":     hold_days,
        })

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    print(f"✅ 추출 완료: {OUTPUT_FILE.name}")
    print(f"   전체 거래: {len(rows)}건")

    buy_rows  = [r for r in rows if r["구분"] == "매수"]
    sell_rows = [r for r in rows if r["구분"] == "매도"]
    print(f"   매수: {len(buy_rows)}건  /  매도: {len(sell_rows)}건")

    if sell_rows:
        pnls      = [int(r["손익금액(원)"]) for r in sell_rows if r["손익금액(원)"] != ""]
        pnl_rates = [float(r["손익률(%)"]) for r in sell_rows if r["손익률(%)"] != ""]
        wins      = [p for p in pnls if p > 0]
        losses    = [p for p in pnls if p < 0]

        print(f"\n📊 매도 요약")
        print(f"   실현 손익    : {sum(pnls):+,}원")
        print(f"   승률         : {len(wins)}/{len(pnls)} ({len(wins)/len(pnls)*100:.1f}%)" if pnls else "")
        if pnl_rates:
            print(f"   평균 손익률  : {sum(pnl_rates)/len(pnl_rates):.2f}%")
            print(f"   최대 수익률  : {max(pnl_rates):.2f}%")
            print(f"   최대 손실률  : {min(pnl_rates):.2f}%")

        triggers: dict[str, int] = {}
        for r in sell_rows:
            k = str(r["거래유형"])
            triggers[k] = triggers.get(k, 0) + 1
        print(f"\n   매도유형별:")
        for k, v in sorted(triggers.items(), key=lambda x: -x[1]):
            pnl_sum = sum(
                int(r["손익금액(원)"]) for r in sell_rows
                if r["거래유형"] == k and r["손익금액(원)"] != ""
            )
            print(f"     {k}: {v}건  ({pnl_sum:+,}원)")


if __name__ == "__main__":
    main()
