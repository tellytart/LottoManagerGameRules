"""Tests for scripts/validate.py, driven by the shared sample files.

The seam is the command line: `validate.py FILE [--base OLDER]`, its exit status and the
reason codes on its output. Every file in tests/valid/ must be accepted and every file in
tests/invalid/ must be rejected with exactly the code tests/expected.json names for it.

These sample files and expected.json are copied into the app's own tests, so its
validator is held to the same answers (see tests/invalid/README.md for the layout).

Layout conventions this file relies on:
  * `<name>.base.json` beside `<name>.json` is the OLDER file to pass as `--base`.
  * `*.base.json` files are not samples in their own right, but each must itself be valid.
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

try:
    import jsonschema
except ImportError:  # pragma: no cover - depends on the environment
    jsonschema = None

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent
VALIDATE = ROOT / "scripts" / "validate.py"
VALID = TESTS / "valid"
INVALID = TESTS / "invalid"
SCHEMA = ROOT / "schema" / "game-rules-v1.schema.json"


def run(path, base=None):
    """Run validate.py on `path`; returns (exit status, stdout, stderr)."""
    cmd = [sys.executable, str(VALIDATE), str(path)]
    if base is not None:
        cmd += ["--base", str(base)]
    done = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    return done.returncode, done.stdout, done.stderr


def reason_codes(stdout):
    """The reason codes on a rejection's output: lines like `REJECT <code> <where>: <message>`."""
    return {line.split()[1] for line in stdout.splitlines() if line.startswith("REJECT ")}


def base_for(path):
    """The `--base` file that goes with a sample, or None."""
    candidate = path.with_name(path.stem + ".base.json")
    return candidate if candidate.exists() else None


def samples(folder):
    """Sample files in a folder, without the `.base.json` companions."""
    return sorted(p for p in folder.glob("*.json") if not p.name.endswith(".base.json"))


class ValidSamplesTests(unittest.TestCase):
    def test_there_are_samples_for_every_required_case(self):
        names = {p.stem for p in samples(VALID)}
        for wanted in ("minimal", "four-games", "unknown-colour", "unknown-field", "unsupported-currency",
                       "rule-set-correction", "held-rule-set-unchanged"):
            self.assertIn(wanted, names)

    def test_every_valid_sample_is_accepted(self):
        for path in samples(VALID):
            with self.subTest(sample=path.name):
                status, out, err = run(path, base_for(path))
                self.assertEqual((status, reason_codes(out)), (0, set()), out + err)
                self.assertTrue(out.startswith("OK"), out)

    def test_every_base_file_is_itself_valid(self):
        for folder in (VALID, INVALID):
            for path in sorted(folder.glob("*.base.json")):
                with self.subTest(base=path.name):
                    status, out, err = run(path)
                    self.assertEqual((status, reason_codes(out)), (0, set()), out + err)

    @unittest.skipUnless(jsonschema, "jsonschema not installed: python3 -m pip install -r requirements.txt")
    def test_valid_samples_also_satisfy_the_json_schema(self):
        # The schema and validate.py describe the same file; a valid sample must satisfy both.
        validator = jsonschema.Draft202012Validator(json.loads(SCHEMA.read_text()))
        for path in sorted(VALID.glob("*.json")):
            with self.subTest(sample=path.name):
                self.assertEqual([e.message for e in validator.iter_errors(json.loads(path.read_text()))], [])


class InvalidSamplesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.expected = json.loads((TESTS / "expected.json").read_text())

    def test_expected_json_lists_every_invalid_sample_and_nothing_else(self):
        self.assertEqual(sorted(self.expected), [p.name for p in samples(INVALID)])

    def test_every_rule_has_a_sample(self):
        # The reason codes documented in tests/invalid/README.md are the full rule list.
        readme = (INVALID / "README.md").read_text()
        for code in set(self.expected.values()):
            self.assertIn(f"`{code}`", readme)

    def test_every_invalid_sample_is_rejected_for_exactly_its_reason(self):
        for name, code in self.expected.items():
            path = INVALID / name
            with self.subTest(sample=name):
                status, out, err = run(path, base_for(path))
                self.assertEqual(status, 1, out + err)
                self.assertEqual(reason_codes(out), {code}, out + err)

    def test_held_rule_set_samples_are_only_bad_against_their_base(self):
        # Without --base the same file is fine: the rule is about comparing with the older copy.
        for name, code in self.expected.items():
            if code != "held-rule-set-changed":
                continue
            with self.subTest(sample=name):
                status, out, err = run(INVALID / name)
                self.assertEqual((status, reason_codes(out)), (0, set()), out + err)


class CommandLineTests(unittest.TestCase):
    def test_a_missing_file_is_a_usage_error_not_a_rejection(self):
        status, out, err = run(TESTS / "no-such-file.json")
        self.assertEqual(status, 2)
        self.assertEqual(reason_codes(out), set())
        self.assertIn("no-such-file.json", err)

    def test_an_unreadable_base_is_a_usage_error(self):
        status, out, err = run(VALID / "minimal.json", base=TESTS / "no-such-base.json")
        self.assertEqual(status, 2)
        self.assertIn("no-such-base.json", err)

    def test_an_invalid_base_is_a_usage_error(self):
        status, out, err = run(VALID / "minimal.json", base=INVALID / "invalid-json.json")
        self.assertEqual(status, 2)

    def test_every_finding_is_reported_not_just_the_first(self):
        # A file with two different problems lists both codes, one REJECT line each.
        broken = json.loads((VALID / "minimal.json").read_text())
        broken["games"][0]["ruleSets"][0]["price"] = 1.5
        broken["games"][0]["timezone"] = "Nowhere/Land"
        # Rewriting the file broke its seal, so the checksum is wrong as well: three findings.
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "broken.json"
            path.write_text(json.dumps(broken, indent=2) + "\n")
            status, out, _ = run(path)
        self.assertEqual(status, 1)
        self.assertEqual(reason_codes(out), {"bad-amount", "bad-timezone", "checksum-wrong"})


if __name__ == "__main__":
    unittest.main()
