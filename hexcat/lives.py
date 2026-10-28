"""Nine lives — a nightly loss budget.

The tarot cards stop rugs *before* entry. Lives are what's left: every stop-loss
that actually hits costs the cat one life. Big wins earn a life back.
At zero lives the cat curls up and stops trading until tomorrow (kill switch).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Lives:
    max: int = 9
    left: int = 9

    def lose(self) -> int:
        self.left = max(0, self.left - 1)
        return self.left

    def gain(self) -> int:
        self.left = min(self.max, self.left + 1)
        return self.left

    @property
    def asleep(self) -> bool:
        return self.left == 0

    def bar(self) -> str:
        return "●" * self.left + "○" * (self.max - self.left)
