#!/usr/bin/env python3
"""Check a game rules file against schema/game-rules-v1.schema.json (the shape only).

Usage:
    check_schema.py FILE

Exit status:
    0   the file fits the schema ("OK <file>" is printed)
    1   the file is not valid JSON, or breaks the schema: one line per problem is printed to
        stdout as `REJECT schema <where>: <message>`, where `<where>` is a path into the file
        such as `games[0].ruleSets[1].price`
    2   this script could not run: unreadable FILE or schema, or `jsonschema` is not installed

The schema is only a first, shape-level gate (and what editors use for hints). The full rules,
including the ones a schema cannot express, live in validate.py, which CI runs as well.

Needs the `jsonschema` package pinned in requirements.txt. The file is read with validate.py's
own JSON parser so both scripts agree on what counts as valid JSON (no NaN, no repeated keys).
"""
import argparse
import json
import sys
from pathlib import Path

# validate.py sits beside this script; put this folder on the import path so it is found
# whether we are run as a script or imported by a test.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import validate  # noqa: E402

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema" / "game-rules-v1.schema.json"


def where(error):
    """A path into the file for a jsonschema error, e.g. `games[0].ruleSets[1].price` (`$` = the root)."""
    text = ""
    for part in error.absolute_path:
        text += f"[{part}]" if isinstance(part, int) else f".{part}"
    return text.lstrip(".") or "$"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check a game rules file against the JSON Schema.")
    parser.add_argument("file", help="the rules file to check")
    args = parser.parse_args(argv)  # a usage error exits with status 2

    try:
        import jsonschema
    except ImportError:
        print("check_schema.py: the jsonschema package is not installed "
              "(python3 -m pip install -r requirements.txt)", file=sys.stderr)
        return 2

    try:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        data = Path(args.file).read_bytes()
    except OSError as err:
        print(f"check_schema.py: cannot read {err.filename}: {err.strerror}", file=sys.stderr)
        return 2

    try:
        document = validate.parse(data)
    except (UnicodeDecodeError, ValueError) as err:
        print(f"REJECT schema $: not valid JSON: {err}")
        return 1

    # sorted by path so the output is stable from run to run
    errors = sorted(jsonschema.Draft202012Validator(schema).iter_errors(document), key=lambda e: list(map(str, e.absolute_path)))
    if not errors:
        print(f"OK {args.file}")
        return 0
    for error in errors:
        print(f"REJECT schema {where(error)}: {error.message}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
