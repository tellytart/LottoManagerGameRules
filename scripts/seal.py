#!/usr/bin/env python3
"""Write, or verify, the checksum on the last line of the game rules file.

The rule (the app's Swift code must reproduce it exactly):

  * The file's last two lines are the checksum line and a closing brace, each
    ending in LF (a Unix newline):

        ...the rest of the JSON, its last member ending in a comma,
          "checksum": "sha256:<64 lowercase hex digits>"
        }

  * The checksum line is exactly two spaces, `"checksum": "sha256:`, 64 lowercase
    hex digits and a closing quote. Nothing else on the line, no trailing comma.
  * The hash is SHA-256 over every byte BEFORE the checksum line, taken from the
    file exactly as stored. It is deliberately NOT a hash of re-serialised JSON:
    Python and Swift print JSON differently, and one differing byte would make the
    app reject a good file.
  * The file must use LF line endings only. `.gitattributes` enforces that for
    `*.json` in git, and `--check` fails on any carriage return.

The checksum catches truncated or corrupted downloads. It does NOT prove who wrote
the file: anyone who can edit the file can recompute it.

Usage:
    seal.py FILE            rewrite FILE in place with a fresh checksum line
    seal.py --check FILE    verify FILE; exit 0 if good, 1 if not, 2 on a usage or I/O error

Only the Python standard library is used.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile

# The exact shape of a well-formed checksum line (without its newline).
CHECKSUM_LINE = re.compile(rb'  "checksum": "sha256:([0-9a-f]{64})"')
# Used when sealing, to recognise and replace an existing checksum line even if it
# is malformed (wrong case, extra spaces), so a bad one can be repaired.
LOOSE_CHECKSUM_LINE = re.compile(rb'\s*"checksum"\s*:.*')
# What every sealed file ends with: the closing brace line after the checksum line.
ENDING = b"}\n"


class ChecksumError(Exception):
    """The file's checksum is missing, malformed or wrong, or the file cannot be sealed."""


def compute_checksum(hashed_bytes: bytes) -> str:
    """The checksum string ("sha256:<hex>") for the bytes before the checksum line."""
    return "sha256:" + hashlib.sha256(hashed_bytes).hexdigest()


def _split(data: bytes) -> tuple[bytes, bytes]:
    """Split a file into (bytes before its last line, that last line without its LF).

    `data` must end with LF + closing brace + LF. The "last line" returned is the
    one just above the closing brace, which is the checksum line in a sealed file.
    """
    if b"\r" in data:
        raise ChecksumError("file contains CR (carriage return) characters; line endings must be LF only")
    if not data.endswith(b"\n" + ENDING):
        raise ChecksumError(
            "file must end with the checksum line, then '}' and a newline (no blank lines, "
            "no missing or extra final newline)"
        )
    body = data[: -len(ENDING)]  # everything up to and including the checksum line's LF
    start = body.rfind(b"\n", 0, len(body) - 1) + 1  # start of the last line
    return body[:start], body[start:-1]


def check(data: bytes) -> str:
    """Verify a sealed file's bytes. Returns the checksum if good, else raises ChecksumError."""
    hashed, line = _split(data)
    match = CHECKSUM_LINE.fullmatch(line)
    if not match:
        raise ChecksumError(
            'the line above the closing "}" is not a well-formed checksum line: expected exactly '
            '`  "checksum": "sha256:<64 lowercase hex digits>"`'
        )
    expected = compute_checksum(hashed)
    found = "sha256:" + match.group(1).decode()
    if found != expected:
        raise ChecksumError(f"checksum does not match the file's bytes (file says {found}, expected {expected})")
    return found


def seal(data: bytes) -> bytes:
    """Return `data` with a correct checksum line as its last line before the closing brace.

    Works on a file with no checksum yet (adds the line, and a comma after the last
    member), a stale or malformed one (replaces it), and a good one (unchanged, so
    sealing twice gives identical bytes). Refuses anything that would not come out
    as valid JSON, so a mistake here can never produce a file the app rejects.
    """
    hashed = _bytes_to_hash(data)
    candidate = hashed + _checksum_line(hashed) + b"\n" + ENDING
    try:
        json.loads(candidate.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as err:
        raise ChecksumError(f"the sealed file would not be valid JSON: {err}") from err
    check(candidate)  # belt and braces: our own output must pass our own check
    return candidate


def _bytes_to_hash(data: bytes) -> bytes:
    """The bytes a fresh checksum must cover: the file minus any existing checksum line.

    If the file has no checksum line yet, the last member gets a trailing comma so
    the checksum line can follow it as the final member.
    """
    if b"\r" in data:
        raise ChecksumError("file contains CR (carriage return) characters; line endings must be LF only")
    if not data.endswith(b"\n" + ENDING):
        raise ChecksumError("file must end with a line containing only '}' and a final newline")
    body = data[: -len(ENDING)]
    start = body.rfind(b"\n", 0, len(body) - 1) + 1
    hashed, line = body[:start], body[start:-1]
    if LOOSE_CHECKSUM_LINE.fullmatch(line):
        return hashed  # existing checksum line: drop it, hash what is above
    if not line.strip():
        raise ChecksumError("the line above the closing '}' is blank")
    if line.strip() == b"{" or line.rstrip().endswith(b","):
        return body  # nothing to fix: empty object, or the last member already has a comma
    return body[:-1] + b",\n"


def _checksum_line(hashed: bytes) -> bytes:
    """The exact checksum line (without its newline) for the given hashed bytes."""
    return f'  "checksum": "{compute_checksum(hashed)}"'.encode()


def _write_in_place(path: str, data: bytes) -> None:
    """Replace a file's contents atomically: write a temp file beside it, then rename."""
    path = os.path.realpath(path)  # if PATH is a symlink, update the file it points to, not the link
    directory = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".seal-")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        shutil.copymode(path, tmp)  # keep the original permissions
        os.replace(tmp, path)
    except BaseException:
        os.unlink(tmp)
        raise


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Write or verify the checksum on the game rules file.")
    parser.add_argument("file", help="path to game-rules.json")
    parser.add_argument("--check", action="store_true", help="verify only; do not change the file")
    args = parser.parse_args(argv)  # a usage error exits with status 2

    try:
        with open(args.file, "rb") as handle:
            data = handle.read()
    except OSError as err:
        print(f"seal.py: cannot read {args.file}: {err.strerror}", file=sys.stderr)
        return 2

    try:
        if args.check:
            print(f"OK {args.file}: {check(data)}")
            return 0
        sealed = seal(data)
        if sealed != data:
            _write_in_place(args.file, sealed)
        print(f"sealed {args.file}: {check(sealed)}")
        return 0
    except ChecksumError as err:
        print(f"seal.py: {args.file}: {err}", file=sys.stderr)
        return 1
    except OSError as err:
        print(f"seal.py: cannot write {args.file}: {err.strerror}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
