"""The graveyard. Every rugger gets a tombstone. The cat never forgets a grave."""
from __future__ import annotations

import sqlite3
import time


class Graveyard:
    def __init__(self, path: str) -> None:
        self.db = sqlite3.connect(path)
        self.db.execute(
            "create table if not exists tombstones(dev text primary key, coin text, cause text, buried_at real, visits int default 0)"
        )
        self.db.commit()

    def bury(self, dev: str, coin: str, cause: str) -> None:
        self.db.execute(
            "insert into tombstones(dev, coin, cause, buried_at) values(?,?,?,?) "
            "on conflict(dev) do update set coin=excluded.coin, cause=excluded.cause",
            (dev, coin, cause, time.time()),
        )
        self.db.commit()

    def visit(self, dev: str) -> tuple[str, str] | None:
        """Has this dev been buried before? Returns (coin, cause)."""
        row = self.db.execute("select coin, cause from tombstones where dev=?", (dev,)).fetchone()
        if row:
            self.db.execute("update tombstones set visits = visits + 1 where dev=?", (dev,))
            self.db.commit()
        return tuple(row) if row else None

    def __len__(self) -> int:
        return self.db.execute("select count(*) from tombstones").fetchone()[0]
