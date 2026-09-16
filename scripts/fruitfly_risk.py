#!/usr/bin/env python3
"""Conservative risk gate for FruitFly signals.

The gate can reject a signal. It does not select a replacement trade.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskLimits:
    max_position_pct: float = 25.0
    max_daily_loss_pct: float = 2.0
    max_drawdown_pct: float = 5.0
    min_strength: float = 0.15


def gate(signal: dict, daily_pnl_pct: float = 0.0, drawdown_pct: float = 0.0,
         consecutive_losses: int = 0, limits: RiskLimits = RiskLimits()) -> dict:
    reasons = []
    if signal.get("signal") not in {"BUY", "SELL", "HOLD"}:
        reasons.append("invalid_signal")
    if signal.get("signal") != "HOLD" and float(signal.get("strength", 0)) < limits.min_strength:
        reasons.append("weak_signal")
    if daily_pnl_pct <= -limits.max_daily_loss_pct:
        reasons.append("daily_loss_limit")
    if drawdown_pct >= limits.max_drawdown_pct:
        reasons.append("drawdown_limit")
    if consecutive_losses >= 3:
        reasons.append("loss_cooldown")
    if signal.get("risk") == "HIGH_VOLATILITY":
        reasons.append("high_volatility")
    return {
        "accepted": not reasons,
        "signal": signal.get("signal", "HOLD") if not reasons else "HOLD",
        "reasons": reasons,
        "max_position_pct": limits.max_position_pct,
        "execution": "NO_ORDERS",
    }
