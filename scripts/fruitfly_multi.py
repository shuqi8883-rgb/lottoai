#!/usr/bin/env python3
"""Multi-asset FruitFly V1 research signal generator.

BTC comes from OKX public candles. ETFs come from Yahoo Finance's public chart
endpoint. This module is read-only: it never places orders.
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
OKX = "https://www.okx.com/api/v5/market/candles"
YAHOO = "https://query1.finance.yahoo.com/v8/finance/chart/{}"

ASSETS = [
    {"id": "BTC-USDT", "name": "Bitcoin", "kind": "crypto", "source": "OKX", "bar": "5m"},
    {"id": "SPY", "name": "SPDR S&P 500 ETF", "kind": "etf", "source": "Yahoo Finance", "bar": "5m"},
    {"id": "QQQ", "name": "Invesco QQQ", "kind": "etf", "source": "Yahoo Finance", "bar": "5m"},
    {"id": "VOO", "name": "Vanguard S&P 500 ETF", "kind": "etf", "source": "Yahoo Finance", "bar": "5m"},
    {"id": "IWM", "name": "iShares Russell 2000 ETF", "kind": "etf", "source": "Yahoo Finance", "bar": "5m"},
]


def http_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "LottoAI-FruitFly/1.0"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_okx(inst_id: str) -> list[dict]:
    q = urllib.parse.urlencode({"instId": inst_id, "bar": "5m", "limit": 120})
    payload = http_json(OKX + "?" + q)
    if payload.get("code") != "0":
        raise RuntimeError(payload.get("msg", "OKX error"))
    rows = []
    for row in reversed(payload.get("data", [])):
        if len(row) >= 9 and row[8] != "1":
            continue
        rows.append({"timestamp": int(row[0]), "close": float(row[4]), "volume": float(row[5])})
    if len(rows) < 10:
        raise RuntimeError("not enough confirmed OKX candles")
    return rows


def fetch_yahoo(ticker: str) -> list[dict]:
    q = urllib.parse.urlencode({"range": "5d", "interval": "5m", "events": "history", "includePrePost": "false"})
    payload = http_json(YAHOO.format(urllib.parse.quote(ticker, safe="")) + "?" + q)
    result = payload.get("chart", {}).get("result", [None])[0]
    if not result:
        raise RuntimeError("Yahoo Finance returned no data")
    timestamps = result.get("timestamp", [])
    quote = result.get("indicators", {}).get("quote", [{}])[0]
    closes = quote.get("close", [])
    volumes = quote.get("volume", [])
    rows = []
    for ts, close, volume in zip(timestamps, closes, volumes):
        if close is None:
            continue
        rows.append({"timestamp": int(ts) * 1000, "close": float(close), "volume": float(volume or 0)})
    if len(rows) < 10:
        raise RuntimeError("not enough ETF candles")
    return rows


def build_signal(rows: list[dict], asset: dict) -> dict:
    prices = [x["close"] for x in rows]
    volumes = [x["volume"] for x in rows]
    brain = FruitFlyBrain()
    action = "HOLD"
    spikes = {"buy_spikes": 0, "sell_spikes": 0, "hold_spikes": 0}
    for i in range(6, len(rows)):
        action, spikes = brain.step(features_from_prices(prices, volumes, i))
    total = max(1, sum(spikes.values()))
    strength = round(min(1.0, abs(spikes["buy_spikes"] - spikes["sell_spikes"]) / total), 4)
    price = prices[-1]
    prev = prices[-2]
    ret_pct = (price / prev - 1.0) * 100 if prev else 0.0
    risk = "HIGH_VOLATILITY" if abs(ret_pct) >= 1.0 else "NORMAL"
    raw = {
        "id": asset["id"], "name": asset["name"], "kind": asset["kind"],
        "source": asset["source"], "timeframe": asset["bar"],
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "candle_timestamp": rows[-1]["timestamp"], "price": price,
        "signal": action, "strength": strength, "risk": risk,
        "return_1_candle_pct": round(ret_pct, 4), "spikes": spikes,
        "engine": "FruitFly V1", "execution": "NO_ORDERS",
    }
    risk_gate = gate(raw)
    raw["risk_gate"] = risk_gate
    raw["signal_actionable"] = bool(risk_gate["accepted"] and action in {"BUY", "SELL"})
    raw["disclaimer"] = "Research signal only; no automatic orders and no profitability guarantee."
    return raw


def main() -> None:
    signals = []
    errors = []
    for asset in ASSETS:
        try:
            rows = fetch_okx(asset["id"]) if asset["kind"] == "crypto" else fetch_yahoo(asset["id"])
            signals.append(build_signal(rows, asset))
        except Exception as exc:
            errors.append({"id": asset["id"], "name": asset["name"], "error": str(exc)})
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "engine": "FruitFly V1",
        "mode": "live-read-only",
        "execution": "NO_ORDERS",
        "assets": signals,
        "errors": errors,
        "note": "BTC uses OKX public market data. ETF data uses Yahoo Finance public chart data and may be delayed/outside market hours.",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
