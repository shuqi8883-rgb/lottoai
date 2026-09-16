#!/usr/bin/env python3
"""Paper-only FruitFly V1 backtest using public OKX market candles.

No API key, order placement, leverage, or withdrawals. This is a research
harness, not a profitability claim.
"""
from __future__ import annotations

import json
import math
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
    prices = [x["close"] for x in candles]
    rows = []
    for i, c in enumerate(candles):
        prev = prices[max(0, i-1)]
        r = (c["close"] / prev - 1.0) if prev else 0.0
        window = prices[max(0, i-12):i+1]
        mom = (c["close"] / window[0] - 1.0) if window and window[0] else 0.0
        if len(window) > 1:
            rets = [window[j] / window[j-1] - 1.0 for j in range(1, len(window))]
            vol = math.sqrt(sum(x*x for x in rets) / len(rets))
        else:
            vol = 0.0
        avg_vol = sum(x["volume"] for x in candles[max(0, i-12):i+1]) / max(1, len(candles[max(0, i-12):i+1]))
        impulse = c["volume"] / avg_vol - 1.0 if avg_vol else 0.0
        rows.append({"return": r, "momentum": mom, "volatility": vol, "volume_impulse": impulse, "price": c["close"]})

    result = backtest(rows, initial_cash=1000.0, fee_rate=0.001, slippage_rate=0.0005)
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
