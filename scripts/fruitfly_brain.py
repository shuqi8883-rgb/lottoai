"""FruitFly Brain V1: a small, deterministic spiking trading experiment.

This is intentionally NOT a claim of reproducing a biological fly. It provides a
safe research harness whose market encoder/readout can later be replaced by a
published MaleCNS/FlyEM connectome. Default mode is paper/backtest only.
"""
from __future__ import annotations
import csv, math, random
from dataclasses import dataclass
from pathlib import Path

@dataclass
class BrainState:
    v: list[float]
    spikes: list[int]
    dopamine: float = 0.0

class FruitFlyBrain:
    """Tiny LIF circuit inspired by the fruit-fly research projects.

    Inputs: normalized return, momentum, volatility and volume impulse.
    Outputs: buy/sell/hold from population spike imbalance.
    """
    def __init__(self, seed: int = 42, n: int = 96):
        self.rng = random.Random(seed)
        self.n = n
        self.w = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for _ in range(5):
                j = self.rng.randrange(n)
                self.w[i][j] = self.rng.uniform(-0.22, 0.30)
        self.state = BrainState([-52.0] * n, [0] * n)

    def step(self, features: tuple[float, float, float, float]) -> tuple[str, dict]:
        ret, mom, vol, volume = features
        sensory = [ret, mom, -vol, volume]
        spikes = [0] * self.n
        for i in range(self.n):
            inp = sensory[i % 4] * (3.0 + (i % 7) * 0.25)
            recurrent = sum(self.w[i][j] * self.state.spikes[j] for j in range(self.n))
            self.state.v[i] += (-(self.state.v[i] + 52.0) / 20.0) + inp + recurrent
            if self.state.v[i] >= -45.0:
                spikes[i] = 1
                self.state.v[i] = -52.0
        self.state.spikes = spikes
        buy = sum(spikes[0::3]); sell = sum(spikes[1::3]); hold = sum(spikes[2::3])
        if buy > sell * 1.15 and buy > hold: action = "BUY"
        elif sell > buy * 1.15 and sell > hold: action = "SELL"
        else: action = "HOLD"
        return action, {"buy_spikes": buy, "sell_spikes": sell, "hold_spikes": hold}

def features_from_prices(prices: list[float], volumes: list[float], i: int) -> tuple[float,float,float,float]:
    p = prices[i]
    ret = math.log(p / prices[i-1]) if i else 0.0
    look = prices[max(0, i-5):i+1]
    momentum = (p / look[0] - 1.0) if look else 0.0
    rets = [math.log(look[k]/look[k-1]) for k in range(1, len(look)) if look[k-1] > 0]
    vol = (sum(x*x for x in rets)/len(rets))**0.5 if rets else 0.0
    base = sum(volumes[max(0,i-5):i+1]) / max(1, len(volumes[max(0,i-5):i+1]))
    volume_impulse = volumes[i] / base - 1.0 if base else 0.0
    return tuple(max(-3.0, min(3.0, x * 100.0)) for x in (ret, momentum, vol, volume_impulse))

def backtest(rows: list[dict], initial: float = 1000.0) -> dict:
    prices = [float(r["close"]) for r in rows]
    volumes = [float(r.get("volume", 1.0)) for r in rows]
    brain = FruitFlyBrain()
    cash, asset = initial, 0.0
    trades = []
    peak = initial; max_dd = 0.0
    for i in range(6, len(rows)):
        action, spikes = brain.step(features_from_prices(prices, volumes, i))
        p = prices[i]
        if action == "BUY" and cash > 0:
            asset = cash / p; cash = 0.0; trades.append((i, "BUY", p, spikes))
        elif action == "SELL" and asset > 0:
            cash = asset * p; asset = 0.0; trades.append((i, "SELL", p, spikes))
        equity = cash + asset * p
        peak = max(peak, equity); max_dd = max(max_dd, (peak-equity)/peak)
    final = cash + asset * prices[-1]
    return {"initial": initial, "final": round(final, 4), "return_pct": round((final/initial-1)*100, 4), "max_drawdown_pct": round(max_dd*100, 4), "trades": len(trades)}

def load_csv(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", help="CSV with close and optional volume columns")
    args = ap.parse_args()
    print(backtest(load_csv(args.csv)))
