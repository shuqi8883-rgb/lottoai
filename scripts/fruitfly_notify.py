#!/usr/bin/env python3
"""Optional Telegram notifier for FruitFly read-only signals.

Secrets are read only from environment variables. No exchange credentials are
used and this script never places trading orders.
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIGNAL = ROOT / "docs" / "flytrade" / "signal.json"
STATE = ROOT / "docs" / "flytrade" / "notify-state.json"


def send_telegram(token: str, chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    body = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    with urllib.request.urlopen(req, timeout=15) as r:
        payload = json.loads(r.read().decode("utf-8"))
    if not payload.get("ok"):
        raise RuntimeError(payload)


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        print("Telegram secrets not configured; notification skipped.")
        return

    signal = json.loads(SIGNAL.read_text(encoding="utf-8"))
    current = signal.get("signal", "HOLD")
    actionable = bool(signal.get("signal_actionable"))
    previous = {}
    if STATE.exists():
        previous = json.loads(STATE.read_text(encoding="utf-8"))
    previous_key = previous.get("key")
    key = f"{signal.get('symbol')}|{signal.get('timeframe')}|{current}|{signal.get('candle_timestamp')}"

    # Notify only actionable BUY/SELL signals once per candle. HOLD is shown on
    # the dashboard but does not generate a push notification.
    if not actionable or current not in {"BUY", "SELL"} or key == previous_key:
        print("No new actionable BUY/SELL notification.")
        return

    gate = signal.get("risk_gate", {})
    reasons = ", ".join(gate.get("reasons", [])) or "none"
    text = (
        f"FruitFly signal\n"
        f"{signal.get('symbol')} {signal.get('timeframe')}\n"
        f"Signal: {current}\n"
        f"Price: {signal.get('price')}\n"
        f"Strength: {signal.get('strength')}\n"
        f"Risk: {signal.get('risk')}\n"
        f"Risk gate: ACCEPTED\n"
        f"Reasons: {reasons}\n"
        f"Execution: NO_ORDERS\n"
        f"Research signal only; no profitability guarantee."
    )
    send_telegram(token, chat_id, text)
    STATE.write_text(json.dumps({"key": key, "updated_at": signal.get("updated_at")}, indent=2), encoding="utf-8")
    print("Telegram notification sent.")


if __name__ == "__main__":
    main()
