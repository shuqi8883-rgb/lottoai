#!/usr/bin/env python3
"""Read-only FruitFly signal engine for live OKX public market data.

This module never places orders. It converts recent confirmed public candles
into the existing FruitFly V1 signal and writes a JSON snapshot.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from fruitfly_brain import FruitFlyBrain, features_from_prices
from fruitfly_risk import gate

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "flytrade" / "signal.json"
BASE = "https://www.okx.com/api/v5/market/candles"


def fetch(inst_id: str = "BTC-USDT", bar: str = "5m", limit: int = 120) -> list[dict]:
    q = urllib.parse.urlencode({"instId": inst_id, "bar": bar, "limit": limit})
    with urllib.request.urlopen(BASE + "?" + q, timeout=20) as r:
        payload = json.loads(r.read().decode("utf-8"))
    if payload.get("code") != "0":
        raise RuntimeError(payload)
    rows = []
    for row in reversed(payload.get("data", [])):
        if len(row) >= 9 and row[8] != "1":
            continue
        rows.append({
            "timestamp": int(row[0]),
            "open": float(row[1]), "high": float(row[2]),
            "low": float(row[3]), "close": float(row[4]),
            "volume": float(row[5]),
        })
    if len(rows) < 10:
        raise RuntimeError("not enough confirmed market candles")
    return rows


def build_signal(rows: list[dict], symbol: str, timeframe: str) -> dict:
    prices = [x["close"] for x in rows]
    volumes = [x["volume"] for x in rows]
    brain = FruitFlyBrain()
    action = "HOLD"
    spikes = {"buy_spikes": 0, "sell_spikes": 0, "hold_spikes": 0}
    for i in range(6, len(rows)):
        action, spikes = brain.step(features_from_prices(prices, volumes, i))
    total = max(1, spikes["buy_spikes"] + spikes["sell_spikes"] + spikes["hold_spikes"])
    side = spikes["buy_spikes"] - spikes["sell_spikes"]
    strength = round(min(1.0, abs(side) / total), 4)
    price = prices[-1]
    prev = prices[-2]
    ret_pct = (price / prev - 1.0) * 100 if prev else 0.0
    risk = "HIGH_VOLATILITY" if abs(ret_pct) >= 1.0 else "NORMAL"
    raw = {
        "mode": "live-read-only",
        "symbol": symbol,
        "timeframe": timeframe,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "candle_timestamp": rows[-1]["timestamp"],
        "price": price,
        "signal": action,
        "strength": strength,
        "risk": risk,
        "return_1_candle_pct": round(ret_pct, 4),
        "spikes": spikes,
        "engine": "FruitFly V1",
        "execution": "NO_ORDERS",
    }
    risk_gate = gate(raw)
    raw["risk_gate"] = risk_gate
    raw["signal_actionable"] = bool(risk_gate["accepted"] and action in {"BUY", "SELL"})
    raw["disclaimer"] = "Live public market signal for research only; not investment advice and not a profitability guarantee."
    return raw


def main() -> None:
    symbol, timeframe = "BTC-USDT", "5m"
    signal = build_signal(fetch(symbol, timeframe), symbol, timeframe)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(signal, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(signal, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
