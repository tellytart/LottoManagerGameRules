"""Tests for scripts/seal.py: the raw-bytes checksum on the rules file's last line.

Run with:  python3 -m unittest discover -s tests -v

The rule under test (shared with the app's Swift code, so keep them in step):
the file's final two lines are `  "checksum": "sha256:<64 lowercase hex>"` and `}`,
each ending in LF. The hash covers every byte BEFORE the checksum line.
"""
import hashlib
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEAL = ROOT / "scripts" / "seal.py"
sys.path.insert(0, str(ROOT / "scripts"))
import seal  # noqa: E402  (path set up just above)

# The bytes the checksum covers in most tests: everything before the checksum line.
PREFIX = b'{\n  "schemaVersion": 1,\n'
# Independently computed with `printf '{\n  "schemaVersion": 1,\n' | shasum -a 256`,
# so a change to the algorithm cannot pass by changing both sides. The app's Swift
# tests should use the same pair.
PREFIX_SHA256 = "2a5658c9bba38a63dd71c9cc915dd043e59ddc02192b1e65061d616cefbb0c6f"


def sealed(prefix: bytes = PREFIX) -> bytes:
    """A correctly sealed file, built by hand (not with seal.py) from a prefix."""
    digest = hashlib.sha256(prefix).hexdigest()
    return prefix + f'  "checksum": "sha256:{digest}"\n}}\n'.encode()


class ComputeTests(unittest.TestCase):
    def test_known_answer(self):
        self.assertEqual(seal.compute_checksum(PREFIX), f"sha256:{PREFIX_SHA256}")

    def test_sealed_helper_matches_known_answer(self):
        self.assertIn(PREFIX_SHA256.encode(), sealed())


class CheckTests(unittest.TestCase):
    def assertRejected(self, data: bytes, fragment: str):
        with self.assertRaises(seal.ChecksumError) as ctx:
            seal.check(data)
        self.assertIn(fragment, str(ctx.exception))

    def test_valid_file_passes(self):
        seal.check(sealed())  # must not raise

    def test_one_changed_byte_fails(self):
        data = bytearray(sealed())
        data[5] ^= 0x01  # flip one bit inside the hashed region
        self.assertRejected(bytes(data), "does not match")

    def test_wrong_digest_fails(self):
        bad = PREFIX + b'  "checksum": "sha256:' + (b"0" * 64) + b'"\n}\n'
        self.assertRejected(bad, "does not match")

    def test_crlf_fails(self):
        self.assertRejected(sealed().replace(b"\n", b"\r\n"), "CR")

    def test_missing_checksum_line_fails(self):
        self.assertRejected(PREFIX + b"  \"games\": []\n}\n", "checksum line")

    def test_empty_file_fails(self):
        self.assertRejected(b"", "checksum line")

    def test_uppercase_hex_fails(self):
        good = sealed().decode()
        upper = good.replace(PREFIX_SHA256, PREFIX_SHA256.upper()).encode()
        self.assertRejected(upper, "checksum line")

    def test_short_digest_fails(self):
        bad = PREFIX + b'  "checksum": "sha256:abc123"\n}\n'
        self.assertRejected(bad, "checksum line")

    def test_wrong_algorithm_prefix_fails(self):
        bad = PREFIX + b'  "checksum": "md5:' + PREFIX_SHA256.encode() + b'"\n}\n'
        self.assertRejected(bad, "checksum line")

    def test_extra_whitespace_in_checksum_line_fails(self):
        base = sealed().decode()
        for variant in (
            base.replace('  "checksum"', '   "checksum"'),        # extra indent
            base.replace('  "checksum"', '\t"checksum"'),          # tab indent
            base.replace('"checksum": "', '"checksum":  "'),       # extra space after colon
            base.replace('"\n}\n', '" \n}\n'),                     # trailing space
        ):
            with self.subTest(variant=variant[-100:]):
                self.assertRejected(variant.encode(), "checksum line")

    def test_missing_final_newline_fails(self):
        self.assertRejected(sealed().rstrip(b"\n"), "checksum line")

    def test_extra_trailing_newline_fails(self):
        self.assertRejected(sealed() + b"\n", "checksum line")

    def test_checksum_line_not_last_fails(self):
        # A checksum line in the middle of the file is not the final line.
        digest = PREFIX_SHA256
        bad = PREFIX + f'  "checksum": "sha256:{digest}",\n  "games": []\n}}\n'.encode()
        self.assertRejected(bad, "checksum line")


class SealTests(unittest.TestCase):
    def test_seal_adds_checksum_to_unsealed_file(self):
        # The last member has no trailing comma yet; sealing adds one, then the line.
        unsealed = b'{\n  "schemaVersion": 1\n}\n'
        out = seal.seal(unsealed)
        seal.check(out)
        self.assertTrue(out.startswith(b'{\n  "schemaVersion": 1,\n  "checksum": "sha256:'))

    def test_seal_replaces_existing_checksum(self):
        stale = PREFIX + b'  "checksum": "sha256:' + (b"0" * 64) + b'"\n}\n'
        out = seal.seal(stale)
        self.assertEqual(out, sealed())

    def test_seal_is_idempotent(self):
        once = seal.seal(b'{\n  "schemaVersion": 1\n}\n')
        self.assertEqual(seal.seal(once), once)

    def test_seal_keeps_hashed_bytes_unchanged_when_already_sealed(self):
        self.assertEqual(seal.seal(sealed()), sealed())

    def test_seal_refuses_crlf(self):
        with self.assertRaises(seal.ChecksumError):
            seal.seal(b'{\r\n  "schemaVersion": 1\r\n}\r\n')

    def test_seal_refuses_invalid_json(self):
        with self.assertRaises(seal.ChecksumError):
            seal.seal(b'{\n  "schemaVersion": 1,,\n}\n')

    def test_seal_refuses_file_not_ending_in_closing_brace_line(self):
        with self.assertRaises(seal.ChecksumError):
            seal.seal(b'{\n  "schemaVersion": 1\n}')

    def test_sealed_output_is_valid_json_with_checksum_member(self):
        import json
        doc = json.loads(seal.seal(b'{\n  "schemaVersion": 1\n}\n'))
        self.assertRegex(doc["checksum"], r"^sha256:[0-9a-f]{64}$")


class CommandLineTests(unittest.TestCase):
    def run_seal(self, *args):
        return subprocess.run([sys.executable, str(SEAL), *args], capture_output=True, text=True)

    def test_seal_then_check_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "rules.json")
            Path(path).write_bytes(b'{\n  "schemaVersion": 1\n}\n')
            self.assertEqual(self.run_seal(path).returncode, 0)
            self.assertEqual(self.run_seal("--check", path).returncode, 0)

    def test_check_exits_nonzero_after_editing_one_byte(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "rules.json")
            Path(path).write_bytes(sealed())
            data = bytearray(Path(path).read_bytes())
            data[5] ^= 0x01
            Path(path).write_bytes(bytes(data))
            result = self.run_seal("--check", path)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("does not match", result.stderr)

    def test_failed_seal_leaves_file_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "rules.json")
            original = b'{\r\n  "schemaVersion": 1\r\n}\r\n'
            Path(path).write_bytes(original)
            self.assertNotEqual(self.run_seal(path).returncode, 0)
            self.assertEqual(Path(path).read_bytes(), original)

    def test_missing_file_is_a_usage_error(self):
        result = self.run_seal("--check", "/nonexistent/rules.json")
        self.assertEqual(result.returncode, 2)

    def test_no_arguments_is_a_usage_error(self):
        self.assertEqual(self.run_seal().returncode, 2)


if __name__ == "__main__":
    unittest.main()
