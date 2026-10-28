"""The eight cards. Each one checks exactly one thing. One red card = TRICK."""
from __future__ import annotations

import asyncio
import re
from collections import defaultdict

import httpx

from .config import Omens
from .feeds.dexscreener import best_pair
from .feeds.solana_rpc import RPC
from .graveyard import Graveyard
from .omen import Card, Omen

PUMP_SUPPLY = 1_000_000_000
LAUNCH_WINDOW_S = 2.5
CURVE_START_VSOL, CURVE_END_VSOL = 30.0, 115.0   # verify current pump.fun curve params before going live
PAID = re.compile(r"\b(ad|paid|promo|sponsored|partner|#ad)\b|100x|1000x|🚀{3,}", re.I)


def the_dev(o: Omen, grave: Graveyard) -> Card:
    """I · THE DEV — has this wallet been buried before?"""
    hit = grave.visit(o.dev)
    if hit:
        return Card("I", "THE DEV", "trick", f"MATCH {hit[0]} ({hit[1]})")
    return Card("I", "THE DEV", "treat", "never seen")


def _launch_buys(o: Omen, trades: list[dict]) -> dict[str, float]:
    early = [t for t in trades if t.get("txType") == "buy" and t["_t"] - o.created_at <= LAUNCH_WINDOW_S]
    by: dict[str, float] = defaultdict(float)
    for t in early:
        by[t["traderPublicKey"]] += float(t.get("tokenAmount", 0))
    return by


def the_bundle(o: Omen, trades: list[dict], om: Omens) -> Card:
    """II · THE BUNDLE — many wallets buying the same seconds as the launch."""
    by = _launch_buys(o, trades)
    pct = 100 * sum(by.values()) / PUMP_SUPPLY
    bad = len(by) >= 4 and pct > om.max_bundle_pct
    return Card("II", "THE BUNDLE", "trick" if bad else "treat", f"{len(by)} wallets · {pct:.0f}%")


def the_sniper(o: Omen, trades: list[dict], om: Omens) -> Card:
    """III · THE SNIPER — non-dev supply taken in ~block 0."""
    by = _launch_buys(o, trades)
    pct = 100 * sum(v for w, v in by.items() if w != o.dev) / PUMP_SUPPLY
    return Card("III", "THE SNIPER", "trick" if pct > om.max_sniper_pct else "treat", f"{pct:.1f}% block 0")


async def the_cluster(o: Omen, rpc: RPC, om: Omens) -> Card:
    """IV · THE CLUSTER — top holders funded by the same wallet (bubblemaps-style)."""
    holders = (await rpc.largest_holders(o.mint))[:15]
    owners = await asyncio.gather(*(rpc.token_account_owner(h["address"]) for h in holders), return_exceptions=True)
    funders = await asyncio.gather(*(rpc.first_funder(w) for w in owners if isinstance(w, str)), return_exceptions=True)
    groups: dict[str, float] = defaultdict(float)
    for h, f in zip(holders, funders):
        if isinstance(f, str):
            groups[f] += float(h.get("uiAmount") or 0)
    funder, amt = max(groups.items(), key=lambda kv: kv[1], default=(None, 0.0))
    pct = 100 * amt / PUMP_SUPPLY
    bad = pct > om.max_cluster_pct or (funder == o.dev and pct > 5)
    return Card("IV", "THE CLUSTER", "trick" if bad else "treat", f"{pct:.0f}% linked" + (" · dev" if funder == o.dev else ""))


async def the_mint(o: Omen, rpc: RPC) -> Card:
    """V · THE MINT — can the dev still print or freeze your bag?"""
    info = await rpc.mint_info(o.mint)
    live = [k for k in ("mintAuthority", "freezeAuthority") if info.get(k)]
    return Card("V", "THE MINT", "trick" if live else "treat", "LIVE: " + "+".join(k[:-9] for k in live) if live else "revoked")


async def the_chart(o: Omen, trades: list[dict], rpc: RPC, http: httpx.AsyncClient, om: Omens) -> Card:
    """VI · THE CHART — top-10 concentration + does anyone manage to sell?"""
    holders = await rpc.largest_holders(o.mint)
    top10 = 100 * sum(float(h.get("uiAmount") or 0) for h in holders[1:11]) / PUMP_SUPPLY
    buyers = {t["traderPublicKey"] for t in trades if t.get("txType") == "buy"}
    sells = sum(1 for t in trades if t.get("txType") == "sell")
    if len(buyers) >= 15 and sells < om.min_sells_seen:
        return Card("VI", "THE CHART", "trick", f"{len(buyers)} buys · 0 sells")
    if top10 > om.max_top10_pct:
        return Card("VI", "THE CHART", "trick", f"top10 {top10:.0f}%")
    pair = await best_pair(http, o.mint)
    if pair and (pair.get("priceChange") or {}).get("m5", 0) < -40:
        return Card("VI", "THE CHART", "warn", "−40% in 5m")
    return Card("VI", "THE CHART", "treat", f"top10 {top10:.0f}%")


async def the_kol(o: Omen, http: httpx.AsyncClient, bearer: str | None, om: Omens) -> Card:
    """VII · THE KOL — organic mentions vs paid shills on X."""
    if not bearer:
        return Card("VII", "THE KOL", "treat", "X off")
    r = await http.get("https://api.x.com/2/tweets/search/recent",
                       params={"query": f"({o.mint} OR \"{o.symbol}\") -is:retweet", "max_results": 50},
                       headers={"Authorization": f"Bearer {bearer}"}, timeout=10)
    if r.status_code != 200:
        return Card("VII", "THE KOL", "warn", f"X {r.status_code}")
    tweets = r.json().get("data", [])
    paid = sum(1 for t in tweets if PAID.search(t["text"]))
    organic = len(tweets) - paid
    v = "trick" if paid > organic else ("treat" if organic >= om.min_organic_kols else "warn")
    return Card("VII", "THE KOL", v, f"{organic} organic · {paid} paid")


def the_curve(o: Omen, trades: list[dict], om: Omens) -> Card:
    """VIII · THE CURVE — where on the bonding curve are we?"""
    v = next((float(t["vSolInBondingCurve"]) for t in reversed(trades) if t.get("vSolInBondingCurve")), None)
    v = v or float(o.meta.get("v_sol") or CURVE_START_VSOL)
    pct = max(0.0, min(100.0, 100 * (v - CURVE_START_VSOL) / (CURVE_END_VSOL - CURVE_START_VSOL)))
    o.curve_pct = pct
    ok = om.min_curve_pct <= pct <= om.max_curve_pct
    return Card("VIII", "THE CURVE", "treat" if ok else "warn", f"{pct:.0f}%")


def verdict(cards: list[Card]) -> str:
    """One red card = TRICK. All green = TREAT. Too many shrugs = skip."""
    if any(c.verdict == "trick" for c in cards):
        return "TRICK"
    if sum(c.verdict == "warn" for c in cards) >= 2:
        return "SKIP"
    return "TREAT"
