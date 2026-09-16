#!/usr/bin/env python3
"""Paper-only FruitFly V1 backtest using public OKX market candles.

No API key, order placement, leverage, or withdrawals. This is a research
harness, not a profitability claim.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from fruitfly_brain import backtest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "flytrade" / "latest.json"
BASE = "https://www.okx.com/api/v5/market/candles"


def fetch(inst_id="BTC-USDT", bar="5m", limit=300):
    q = urllib.parse.urlencode({"instId": inst_id, "bar": bar, "limit": limit})
    with urllib.request.urlopen(BASE + "?" + q, timeout=20) as r:
        payload = json.loads(r.read().decode("utf-8"))
    if payload.get("code") != "0":
        raise RuntimeError(payload)
    rows = []
    for row in reversed(payload.get("data", [])):
        # OKX: ts, open, high, low, close, vol, volCcy, volCcyQuote, confirm
        if len(row) >= 9 and row[8] != "1":
            continue
        rows.append({
            "timestamp": int(row[0]),
            "open": float(row[1]), "high": float(row[2]),
            "low": float(row[3]), "close": float(row[4]),
            "volume": float(row[5]),
        })
    return rows


def main():
    inst = "BTC-USDT"
    bar = "5m"
    candles = fetch(inst, bar)
    if len(candles) < 10:
        raise RuntimeError("not enough confirmed market candles")

    result = backtest(candles, initial=1000.0)
    prices = [x["close"] for x in candles]
    buy_hold = (prices[-1] / prices[0] - 1.0) * 100 if prices else 0.0
    output = {
        "mode": "paper",
        "symbol": inst,
        "timeframe": bar,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "candles": len(candles),
        "last_price": prices[-1] if prices else None,
        "fruitfly": result,
        "buy_and_hold_return_pct": round(buy_hold, 4),
        "disclaimer": "Research backtest only. No profitability guarantee. No live orders.",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
