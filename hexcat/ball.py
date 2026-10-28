"""The crystal ball. Coins fall in, the cat draws eight cards, and decides: trick or treat."""
from __future__ import annotations

import asyncio

import httpx
from rich.console import Console

from . import tarot
from .config import Config
from .feeds.pumpportal import PumpPortal
from .feeds.solana_rpc import RPC
from .graveyard import Graveyard
from .ledger import Ledger, Position
from .lives import Lives
from .omen import Card, Omen
from .wand import Wand

con = Console()
GAZE_S = 6.0  # let the launch play out: bundles and snipers reveal themselves in the first seconds
ICON = {"treat": "[bold green]✓[/]", "warn": "[yellow]~[/]", "trick": "[bold red]✕[/]"}


def last_price(trades: list[dict]) -> float | None:
    for t in reversed(trades):
        sol, tok = float(t.get("solAmount") or 0), float(t.get("tokenAmount") or 0)
        if sol and tok:
            return sol / tok
    return None


class CrystalBall:
    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.http = httpx.AsyncClient(headers={"user-agent": "hexcat/0.1"})
        self.rpc = RPC(cfg.rpc_url, self.http)
        self.feed = PumpPortal()
        self.grave = Graveyard(cfg.graveyard_path)
        self.lives = Lives(cfg.lives, cfg.lives)
        self.ledger = Ledger(cfg.exits)
        self.wand = Wand(self.http, self.rpc, cfg.live, cfg.private_key_b58)
        self.bag: dict[str, Position] = {}

    async def draw_cards(self, o: Omen) -> list[Card]:
        om, trades = self.cfg.omens, self.feed.trades.get(o.mint, [])
        dev = tarot.the_dev(o, self.grave)
        if dev.verdict == "trick":  # known rugger: don't even shuffle the deck
            return [dev]
        cards = [dev, tarot.the_bundle(o, trades, om), tarot.the_sniper(o, trades, om), tarot.the_curve(o, trades, om)]
        slow = await asyncio.gather(
            tarot.the_cluster(o, self.rpc, om), tarot.the_mint(o, self.rpc),
            tarot.the_chart(o, trades, self.rpc, self.http, om), tarot.the_kol(o, self.http, self.cfg.x_bearer, om),
            return_exceptions=True,
        )
        for c in slow:
            cards.append(c if isinstance(c, Card) else Card("?", "THE VOID", "warn", type(c).__name__))
        order = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "?"]
        return sorted(cards, key=lambda c: order.index(c.numeral))

    async def gaze(self, o: Omen) -> None:
        if self.lives.asleep:
            return
        await asyncio.sleep(GAZE_S)
        cards = await self.draw_cards(o)
        v = tarot.verdict(cards)
        con.print(f"\n[bold]{o.symbol}[/] [dim]{o.mint[:6]}…{o.mint[-4:]}[/]")
        for c in cards:
            con.print(f"  {ICON[c.verdict]} [magenta]{c.numeral:>4}[/] {c.name:<12} {c.reading}")
        if v == "TRICK":
            cause = next(c.reading for c in cards if c.verdict == "trick")
            self.grave.bury(o.dev, o.symbol, cause)
            con.print(f"  [bold magenta]TRICK![/] [red]{cause}[/]  [dim]🪦 tombstone #{len(self.grave)}[/]")
            await self.feed.forget(o.mint)
        elif v == "TREAT":
            size = self.cfg.exits.size_sol
            res = await self.wand.trade("buy", o.mint, size, True)
            px = last_price(self.feed.trades.get(o.mint, [])) or 0
            self.bag[o.mint] = Position(o.mint, o.symbol, px, size)
            con.print(f"  [bold green]TREAT![/] 8/8 cards · buy {size} SOL {'(paper)' if res.get('paper') else res.get('sig')}")
        else:
            con.print("  [dim]the cat shrugs. skip.[/]")
            await self.feed.forget(o.mint)

    async def watch_bag(self) -> None:
        while True:
            await asyncio.sleep(1.0)
            for mint, p in list(self.bag.items()):
                px = last_price(self.feed.trades.get(mint, []))
                if not px or not p.entry:
                    continue
                for reason, frac in self.ledger.step(p, px):
                    await self.wand.trade("sell", mint, f"{int(frac * 100)}%", False)
                    pnl = p.size_sol * frac * (px / p.entry - 1)
                    p.left -= frac
                    self.ledger.book(pnl)
                    if reason == "SL":
                        self.lives.lose()
                        con.print(f"[red]SL {p.symbol}[/] {pnl:+.3f} SOL · [bold]−1 LIFE[/] {self.lives.bar()}")
                    else:
                        if reason == "TP2":
                            self.lives.gain()
                        con.print(f"[green]{reason} {p.symbol}[/] {pnl:+.3f} SOL · night {self.ledger.realized_sol:+.3f} · {self.lives.bar()}")
                if p.left <= 1e-6:
                    del self.bag[mint]
                    await self.feed.forget(mint)
            if self.lives.asleep and not self.bag:
                con.print("\n[bold magenta]0 lives left. the cat curls up and sleeps until tomorrow. 💤[/]")
                raise SystemExit(0)

    async def run(self) -> None:
        mode = "[bold red]LIVE[/]" if self.cfg.live else "[bold cyan]PAPER[/]"
        con.print(f"[bold orange1]HEXCAT[/] awake · {mode} · lives {self.lives.bar()} · {len(self.grave)} graves")
        asyncio.create_task(self.watch_bag())
        async for o in self.feed.stream():
            asyncio.create_task(self.gaze(o))
