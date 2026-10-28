from __future__ import annotations

import os
from dataclasses import dataclass, field

import yaml


@dataclass
class Omens:
    """How paranoid the cat is. One card past its limit = TRICK."""
    max_bundle_pct: float = 15.0     # % supply bought by linked wallets in the launch window
    max_sniper_pct: float = 12.0     # % supply sniped in ~block 0
    max_cluster_pct: float = 20.0    # top holders sharing one funder
    max_top10_pct: float = 35.0      # top-10 holders excl. curve / AMM vault
    min_organic_kols: int = 2
    min_curve_pct: float = 8.0
    max_curve_pct: float = 92.0
    min_sells_seen: int = 1          # THE CHART: no sells while many buys = honeypot smell


@dataclass
class Exits:
    size_sol: float = 1.5
    tp_ladder: list[tuple[float, float]] = field(default_factory=lambda: [(1.0, 0.4), (3.0, 0.4)])
    trailing_runner_pct: float = 20.0
    stop_loss_pct: float = 35.0


@dataclass
class Config:
    rpc_url: str = "https://api.mainnet-beta.solana.com"
    live: bool = False
    private_key_b58: str | None = None
    x_bearer: str | None = None
    graveyard_path: str = "graveyard.sqlite"
    lives: int = 9                   # stop-losses allowed per night before the cat goes to sleep
    omens: Omens = field(default_factory=Omens)
    exits: Exits = field(default_factory=Exits)

    @classmethod
    def load(cls, path: str | None = None) -> "Config":
        raw: dict = {}
        if path and os.path.exists(path):
            with open(path) as f:
                raw = yaml.safe_load(f) or {}
        ex = raw.get("exits", {})
        if "tp_ladder" in ex:
            ex["tp_ladder"] = [tuple(x) for x in ex["tp_ladder"]]
        c = cls(
            rpc_url=os.getenv("HEXCAT_RPC_URL", raw.get("rpc_url", cls.rpc_url)),
            live=os.getenv("HEXCAT_LIVE", str(raw.get("live", False))).lower() in ("1", "true", "yes"),
            private_key_b58=os.getenv("HEXCAT_PRIVATE_KEY"),
            x_bearer=os.getenv("HEXCAT_X_BEARER"),
            graveyard_path=raw.get("graveyard_path", cls.graveyard_path),
            lives=int(raw.get("lives", 9)),
            omens=Omens(**raw.get("omens", {})),
            exits=Exits(**ex),
        )
        if c.live and not c.private_key_b58:
            raise SystemExit("HEXCAT_LIVE=1 needs HEXCAT_PRIVATE_KEY (burner wallet only). The cat refuses.")
        return c
