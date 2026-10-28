"""The Soul Ledger — positions, the take-profit ladder, realized P&L."""
from __future__ import annotations

from dataclasses import dataclass, field

from .config import Exits


@dataclass
class Position:
    mint: str
    symbol: str
    entry: float
    size_sol: float
    left: float = 1.0
    peak: float = 0.0
    hit: set[int] = field(default_factory=set)


@dataclass
class Ledger:
    ex: Exits
    realized_sol: float = 0.0
    wins: int = 0
    losses: int = 0

    def step(self, p: Position, price: float) -> list[tuple[str, float]]:
        """Returns [(reason, fraction_of_original_bag)] to sell."""
        out: list[tuple[str, float]] = []
        gain = price / p.entry - 1
        p.peak = max(p.peak, price)
        if gain <= -self.ex.stop_loss_pct / 100 and p.left > 0:
            return [("SL", p.left)]
        for i, (tp, frac) in enumerate(self.ex.tp_ladder):
            if gain >= tp and i not in p.hit and p.left > 0:
                p.hit.add(i)
                out.append((f"TP{i + 1}", min(frac, p.left)))
        if len(p.hit) == len(self.ex.tp_ladder) and p.left > 0 and price <= p.peak * (1 - self.ex.trailing_runner_pct / 100):
            out.append(("runner", p.left))
        return out

    def book(self, pnl_sol: float) -> None:
        self.realized_sol += pnl_sol
        if pnl_sol >= 0:
            self.wins += 1
        else:
            self.losses += 1
