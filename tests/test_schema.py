"""Tests for schema/game-rules-v1.schema.json.

The schema checks shape only. These tests feed it small hand-built documents:
ones it must accept (including the shapes the four v1 games need) and ones it
must reject. They need the `jsonschema` package (pinned in requirements.txt):

    python3 -m pip install -r requirements.txt

Without it the tests are skipped, so a plain `python3 -m unittest` still works
for the seal tests; CI installs it, so nothing is skipped there.
"""
import copy
import json
import unittest
from pathlib import Path

try:
    import jsonschema
except ImportError:  # pragma: no cover - depends on the environment
    jsonschema = None

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema" / "game-rules-v1.schema.json"
CHECKSUM = "sha256:" + "0" * 64


def lotto():
    """Lotto: two Rounds, a Bonus Ball drawn from the main balls, a variable jackpot."""
    return {
        "id": "lotto", "name": "Lotto", "currency": "GBP", "timezone": "Europe/London", "endsAfter": None,
        "ballSchemes": {"main": [{"from": 1, "to": 9, "color": "white"}, {"from": 10, "to": 19, "color": "blue"}]},
        "ruleSets": [{
            "id": "lotto-2026-06-10-r1", "effectiveFrom": "2026-06-10", "price": 200, "rounds": 2, "claimDays": 180,
            "draws": [{"weekday": "wed", "cutOff": "19:30", "live": "20:00", "results": "21:30"}],
            "numbers": {"main": {"count": 6, "min": 1, "max": 59}, "extras": [{"kind": "bonusBall", "count": 1}]},
            "tiers": [
                {"id": "jackpot", "name": "Jackpot", "match": {"main": 6}, "prize": {"kind": "variable"}},
                {"id": "match-5-bonus", "name": "Match 5 + Bonus Ball",
                 "match": {"main": 5, "bonusBall": True}, "prize": {"kind": "fixed", "amount": 100000000}},
                {"id": "match-3", "name": "Match 3", "match": {"main": 3}, "prize": {"kind": "fixed", "amount": 1000}},
            ],
            "raffle": {"name": "Guaranteed Millionaire Raffle", "everyDraw": False},
        }],
    }


def euromillions():
    """EuroMillions: a separate set of Lucky Stars, every prize typed by the manager, a raffle."""
    return {
        "id": "euromillions", "name": "EuroMillions", "currency": "GBP", "timezone": "Europe/London",
        "ballSchemes": {"main": [{"from": 1, "to": 50, "color": "blue"}], "Lucky Stars": [{"from": 1, "to": 12, "color": "gold"}]},
        "ruleSets": [{
            "id": "euromillions-2025-07-28-r1", "effectiveFrom": "2025-07-28", "price": 250, "rounds": 1,
            "draws": [{"weekday": "tue", "cutOff": "19:30", "live": "20:15", "results": "21:00"}],
            "numbers": {"main": {"count": 5, "min": 1, "max": 50},
                        "extras": [{"kind": "separateSet", "name": "Lucky Stars", "count": 2, "min": 1, "max": 12}]},
            "tiers": [{"id": "jackpot", "name": "5 + 2 Lucky Stars", "match": {"main": 5, "extras": {"Lucky Stars": 2}},
                       "prize": {"kind": "variable"}}],
            "raffle": {"name": "UK Millionaire Maker", "everyDraw": True},
        }],
    }


def set_for_life():
    """Set For Life: an instalments prize (monthly, 360 payments)."""
    return {
        "id": "set-for-life", "name": "Set For Life", "currency": "GBP", "timezone": "Europe/London",
        "ballSchemes": {"main": [{"from": 1, "to": 47, "color": "purple"}], "Life Ball": [{"from": 1, "to": 10, "color": "gold"}]},
        "ruleSets": [{
            "id": "set-for-life-2025-07-28-r1", "effectiveFrom": "2025-07-28", "price": 150, "rounds": 1,
            "draws": [{"weekday": "mon", "cutOff": "19:30", "live": "20:00", "results": "20:30"}],
            "numbers": {"main": {"count": 5, "min": 1, "max": 47},
                        "extras": [{"kind": "separateSet", "name": "Life Ball", "count": 1, "min": 1, "max": 10}]},
            "tiers": [{"id": "5-life-ball", "name": "5 + Life Ball", "match": {"main": 5, "extras": {"Life Ball": 1}},
                       "prize": {"kind": "instalments", "amount": 1000000, "count": 360, "everyMonths": 1}}],
        }],
    }


def document():
    return {"schemaVersion": 1, "checkedOn": "2026-09-19", "games": [lotto(), euromillions(), set_for_life()],
            "checksum": CHECKSUM}


@unittest.skipUnless(jsonschema, "jsonschema not installed: python3 -m pip install -r requirements.txt")
class SchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads(SCHEMA_PATH.read_text())
        cls.validator = jsonschema.Draft202012Validator(cls.schema)

    def errors(self, doc):
        return list(self.validator.iter_errors(doc))

    def assertAccepts(self, doc):
        self.assertEqual([e.message for e in self.errors(doc)], [])

    def assertRejects(self, doc, msg=""):
        self.assertTrue(self.errors(doc), f"schema accepted a bad document: {msg}")

    def mutated(self, change):
        """A copy of the full document with `change(doc)` applied."""
        doc = copy.deepcopy(document())
        change(doc)
        return doc

    def test_schema_is_itself_valid(self):
        jsonschema.Draft202012Validator.check_schema(self.schema)

    # ---- documents that must pass ----
    def test_accepts_the_four_v1_game_shapes(self):
        self.assertAccepts(document())

    def test_accepts_unknown_extra_fields_everywhere(self):
        def add(doc):
            doc["futureField"] = 1
            game = doc["games"][0]
            game["futureField"] = 1
            rs = game["ruleSets"][0]
            rs["futureField"] = {"a": 1}
            rs["tiers"][0]["futureField"] = True
            rs["draws"][0]["futureField"] = "x"
        self.assertAccepts(self.mutated(add))

    def test_accepts_end_date_null_or_a_date_and_missing_optionals(self):
        def change(doc):
            doc["games"][0]["endsAfter"] = "2030-01-01"
            del doc["games"][1]["ruleSets"][0]["raffle"]  # raffle is optional
            del doc["games"][0]["ruleSets"][0]["claimDays"]
            doc["games"][0]["ruleSets"][0]["raffle"] = None
        self.assertAccepts(self.mutated(change))

    def test_accepts_an_unknown_ball_colour_name(self):
        self.assertAccepts(self.mutated(lambda d: d["games"][0]["ballSchemes"]["main"][0].update(color="chartreuse")))

    # ---- documents that must fail ----
    def test_rejects_missing_top_level_members(self):
        for key in ("schemaVersion", "checkedOn", "games", "checksum"):
            with self.subTest(missing=key):
                self.assertRejects(self.mutated(lambda d, k=key: d.pop(k)), key)

    def test_rejects_wrong_schema_version(self):
        self.assertRejects(self.mutated(lambda d: d.update(schemaVersion=2)))

    def test_rejects_malformed_checksum_member(self):
        for bad in ("sha256:ABC", "md5:" + "0" * 32, "sha256:" + "G" * 64, "sha256:" + "A" * 64, 5):
            with self.subTest(bad=bad):
                self.assertRejects(self.mutated(lambda d, b=bad: d.update(checksum=b)))

    def test_rejects_empty_games(self):
        self.assertRejects(self.mutated(lambda d: d.update(games=[])))

    def test_rejects_bad_dates(self):
        for bad in ("19/09/2026", "2026-9-19", "2026-13-01", "2026-00-10", "tomorrow", 20260919):
            with self.subTest(bad=bad):
                self.assertRejects(self.mutated(lambda d, b=bad: d.update(checkedOn=b)))
        self.assertRejects(self.mutated(lambda d: d["games"][0]["ruleSets"][0].update(effectiveFrom="10 June")))

    def test_rejects_prices_and_amounts_that_are_not_whole_minor_units(self):
        rs = lambda d: d["games"][0]["ruleSets"][0]
        for bad in (2.5, -200, "200", None):
            with self.subTest(price=bad):
                self.assertRejects(self.mutated(lambda d, b=bad: rs(d).update(price=b)))
        self.assertRejects(self.mutated(lambda d: rs(d)["tiers"][2]["prize"].update(amount=10.5)))
        self.assertRejects(self.mutated(lambda d: rs(d)["tiers"][2]["prize"].pop("amount")))

    def test_rejects_bad_currency(self):
        for bad in ("gbp", "GB", "POUND", 826):
            with self.subTest(currency=bad):
                self.assertRejects(self.mutated(lambda d, b=bad: d["games"][0].update(currency=b)))

    def test_rejects_bad_times_and_weekdays(self):
        draw = lambda d: d["games"][0]["ruleSets"][0]["draws"][0]
        for bad in ("7:30pm", "19:30:00", "24:00", "19:60", "1930"):
            with self.subTest(time=bad):
                self.assertRejects(self.mutated(lambda d, b=bad: draw(d).update(cutOff=b)))
        for bad in ("wednesday", "Wed", "8"):
            with self.subTest(weekday=bad):
                self.assertRejects(self.mutated(lambda d, b=bad: draw(d).update(weekday=b)))

    def test_rejects_bad_rule_set_ids(self):
        for bad in ("lotto-2026-06-10", "lotto-2026-06-10-r0", "lotto-2026-06-10-1", "Lotto-2026-06-10-r1", "r1"):
            with self.subTest(id=bad):
                self.assertRejects(self.mutated(lambda d, b=bad: d["games"][0]["ruleSets"][0].update(id=b)))

    def test_rejects_unknown_prize_and_extra_kinds(self):
        self.assertRejects(self.mutated(lambda d: d["games"][0]["ruleSets"][0]["tiers"][0].update(prize={"kind": "freeLine"})))
        self.assertRejects(self.mutated(lambda d: d["games"][0]["ruleSets"][0]["numbers"].update(extras=[{"kind": "powerball", "count": 1}])))

    def test_rejects_instalments_missing_their_schedule(self):
        def change(doc):
            del doc["games"][2]["ruleSets"][0]["tiers"][0]["prize"]["everyMonths"]
        self.assertRejects(self.mutated(change))

    def test_rejects_separate_set_without_a_range(self):
        def change(doc):
            del doc["games"][1]["ruleSets"][0]["numbers"]["extras"][0]["max"]
        self.assertRejects(self.mutated(change))

    def test_rejects_missing_required_rule_set_members(self):
        for key in ("id", "effectiveFrom", "price", "rounds", "draws", "numbers", "tiers"):
            with self.subTest(missing=key):
                self.assertRejects(self.mutated(lambda d, k=key: d["games"][0]["ruleSets"][0].pop(k)))

    def test_rejects_empty_tier_list_and_empty_draw_list(self):
        self.assertRejects(self.mutated(lambda d: d["games"][0]["ruleSets"][0].update(tiers=[])))
        self.assertRejects(self.mutated(lambda d: d["games"][0]["ruleSets"][0].update(draws=[])))

    def test_rejects_zero_rounds_and_missing_main_ball_scheme(self):
        self.assertRejects(self.mutated(lambda d: d["games"][0]["ruleSets"][0].update(rounds=0)))
        self.assertRejects(self.mutated(lambda d: d["games"][0]["ballSchemes"].pop("main")))

    def test_rejects_bad_raffle(self):
        self.assertRejects(self.mutated(lambda d: d["games"][0]["ruleSets"][0].update(raffle={"name": "X"})))
        self.assertRejects(self.mutated(lambda d: d["games"][0]["ruleSets"][0].update(raffle="yes")))


if __name__ == "__main__":
    unittest.main()
