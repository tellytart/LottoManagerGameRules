"""Tests for the real rules file, v1/game-rules.json, the file the app fetches.

The other tests check the scripts against small sample files. These check the published
file itself, so a bad edit (a typo, a stale checksum, a changed held rule set) fails here as
well as in the CI workflow, before a pull request is even opened. Run with:

    python3 -m unittest discover -s tests -v
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RULES = ROOT / "v1" / "game-rules.json"
# A byte-for-byte copy of the rules file among the shared samples, so the app's own tests
# run against the real file too. Refresh it whenever the rules file changes (see CHECKLIST.md).
SAMPLE_COPY = ROOT / "tests" / "valid" / "current-game-rules.json"


def run_script(name, *args):
    """Run scripts/<name> and return (exit status, stdout + stderr)."""
    result = subprocess.run([sys.executable, str(ROOT / "scripts" / name), *map(str, args)],
                            capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr


class RulesFileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.doc = json.loads(RULES.read_text(encoding="utf-8"))

    def test_passes_the_full_validation_rules(self):
        status, output = run_script("validate.py", RULES)
        self.assertEqual(status, 0, output)

    def test_checksum_is_current(self):
        status, output = run_script("seal.py", "--check", RULES)
        self.assertEqual(status, 0, output)

    def test_has_the_four_games(self):
        self.assertEqual([g["id"] for g in self.doc["games"]],
                         ["lotto", "euromillions", "thunderball", "set-for-life"])

    def test_every_game_has_one_current_rule_set_with_a_matching_id(self):
        for game in self.doc["games"]:
            with self.subTest(game=game["id"]):
                self.assertEqual(len(game["ruleSets"]), 1)
                rule_set = game["ruleSets"][0]
                self.assertEqual(rule_set["id"], f"{game['id']}-{rule_set['effectiveFrom']}-r1")

    def test_facts_shared_by_every_game(self):
        for game in self.doc["games"]:
            with self.subTest(game=game["id"]):
                self.assertEqual((game["currency"], game["timezone"]), ("GBP", "Europe/London"))
                rule_set = game["ruleSets"][0]
                self.assertEqual(rule_set["claimDays"], 180)
                for draw in rule_set["draws"]:
                    self.assertEqual(draw["cutOff"], "19:30")

    def test_lotto_has_two_rounds(self):
        # Pre-June 2026 Lotto (one Round) is deliberately not in the file.
        lotto = self.doc["games"][0]["ruleSets"][0]
        self.assertEqual((lotto["id"], lotto["rounds"]), ("lotto-2026-06-10-r1", 2))

    def test_the_sample_copy_is_identical(self):
        self.assertEqual(SAMPLE_COPY.read_bytes(), RULES.read_bytes(),
                         "tests/valid/current-game-rules.json is out of step: "
                         "cp v1/game-rules.json tests/valid/current-game-rules.json")


if __name__ == "__main__":
    unittest.main()
