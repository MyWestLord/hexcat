import argparse
import asyncio

from .ball import CrystalBall
from .config import Config

CAT = r"""
        /\_/\        _   _ _______  __ ____    _  _____
   ___ ( o.O )      | | | | ____\ \/ // ___|  / \|_   _|
  /   \ > ^ <       | |_| |  _|  \  /| |     / _ \ | |
 / ~~~ \  |\_/|     |  _  | |___ /  \| |___ / ___ \| |
 \_____/  ( O.o)    |_| |_|_____/_/\_\\____/_/   \_\_|
            9 lives · 8 cards · rugs get tombstones
"""


def main() -> None:
    ap = argparse.ArgumentParser(prog="hexcat", description="the pump.fun bot with 9 lives")
    ap.add_argument("-c", "--config", default="config.yaml")
    ap.add_argument("--live", action="store_true", help="real trades (burner wallet only). default: paper")
    a = ap.parse_args()
    cfg = Config.load(a.config)
    if a.live:
        cfg.live = True
        if not cfg.private_key_b58:
            raise SystemExit("--live needs HEXCAT_PRIVATE_KEY (burner wallet only).")
    print(CAT)
    try:
        asyncio.run(CrystalBall(cfg).run())
    except KeyboardInterrupt:
        print("\nthe cat wanders off into the night. 🐈‍⬛")


if __name__ == "__main__":
    main()
