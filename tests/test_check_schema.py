"""Tests for scripts/check_schema.py: the CI step that checks a rules file against the JSON Schema.

It is run as a subprocess, the way the workflow runs it, so the exit status and output
are what CI sees. The valid and invalid samples are reused from tests/ rather than
duplicated. Needs the `jsonschema` package (pinned in requirements.txt); skipped without it,
and CI fails loudly if it is missing, so nothing is skipped there.
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

try:
    import jsonschema  # noqa: F401
except ImportError:  # pragma: no cover - depends on the environment
    jsonschema = None

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "check_schema.py"
VALID = ROOT / "tests" / "valid"
INVALID = ROOT / "tests" / "invalid"


def run(*args):
    """Run check_schema.py with `args`; returns (exit status, stdout, stderr)."""
    result = subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


@unittest.skipIf(jsonschema is None, "jsonschema is not installed")
class CheckSchemaTests(unittest.TestCase):
    def test_accepts_a_valid_file(self):
        status, out, _ = run(VALID / "four-games.json")
        self.assertEqual(status, 0)
        self.assertIn("OK", out)

    def test_rejects_a_file_that_breaks_the_schema(self):
        # The unknown prize kind is a shape error the schema is meant to catch.
        status, out, _ = run(INVALID / "malformed-structure--unknown-prize-kind.json")
        self.assertEqual(status, 1)
        self.assertIn("REJECT", out)

    def test_names_where_the_problem_is(self):
        _, out, _ = run(INVALID / "malformed-structure--unknown-prize-kind.json")
        self.assertIn("games", out)  # a path into the file, not just "invalid"

    def test_rejects_invalid_json(self):
        status, out, _ = run(INVALID / "invalid-json.json")
        self.assertEqual(status, 1)
        self.assertIn("REJECT", out)

    def test_rejects_a_duplicate_key(self):
        # validate.py refuses these too; the schema step must not be looser than it.
        status, _, _ = run(INVALID / "invalid-json--duplicate-key.json")
        self.assertEqual(status, 1)

    def test_missing_file_is_a_setup_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            status, out, err = run(Path(tmp) / "nope.json")
        self.assertEqual(status, 2)
        self.assertEqual(out, "")
        self.assertIn("cannot read", err)

    def test_every_valid_sample_passes(self):
        for sample in sorted(VALID.glob("*.json")):
            with self.subTest(sample=sample.name):
                self.assertEqual(run(sample)[0], 0)


if __name__ == "__main__":
    unittest.main()
