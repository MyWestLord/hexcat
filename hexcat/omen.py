"""Omens: a new coin entering the crystal ball, and the cards drawn for it."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Verdict = Literal["treat", "warn", "trick"]


@dataclass
class Omen:
    """A freshly minted coin. The cat stares at it."""
    mint: str
    symbol: str
    name: str
    dev: str
    source: str  # "pump" | "dex"
    created_at: float
    market_cap_sol: float = 0.0
    curve_pct: float | None = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class Card:
    """One tarot card drawn for one coin."""
    numeral: str      # I..VIII
    name: str         # THE BUNDLE
    verdict: Verdict
    reading: str      # "6 wallets · 31%"
