from hexcat import tarot
from hexcat.config import Exits, Omens
from hexcat.graveyard import Graveyard
from hexcat.ledger import Ledger, Position
from hexcat.lives import Lives
from hexcat.omen import Card, Omen


def test_one_red_card_is_a_trick():
    cards = [Card("I", "THE DEV", "treat", "")] * 7 + [Card("II", "THE BUNDLE", "trick", "6 wallets")]
    assert tarot.verdict(cards) == "TRICK"


def test_eight_green_cards_is_a_treat():
    assert tarot.verdict([Card("I", "x", "treat", "")] * 8) == "TREAT"


def test_the_cat_never_forgets_a_grave(tmp_path):
    g = Graveyard(str(tmp_path / "g.sqlite"))
    g.bury("DEV1", "$GHOSTY", "bundle")
    o = Omen("MINT2", "$GHOSTY2", "", "DEV1", "pump", 0.0)
    card = tarot.the_dev(o, g)
    assert card.verdict == "trick" and "$GHOSTY" in card.reading


def test_bundle_and_snipers():
    o = Omen("M", "$X", "", "DEV", "pump", 1000.0)
    trades = [{"txType": "buy", "traderPublicKey": f"W{i}", "tokenAmount": 50_000_000, "_t": 1000.4} for i in range(6)]
    assert tarot.the_bundle(o, trades, Omens()).verdict == "trick"
    assert tarot.the_sniper(o, trades, Omens()).verdict == "trick"


def test_nine_lives_kill_switch():
    l = Lives()
    for _ in range(9):
        l.lose()
    assert l.asleep and l.bar() == "○" * 9
    l.gain()
    assert not l.asleep


def test_tp_ladder():
    led = Ledger(Exits())
    p = Position("M", "$P", 1.0, 1.5)
    assert led.step(p, 2.05) == [("TP1", 0.4)]
    assert led.step(p, 4.2) == [("TP2", 0.4)]
