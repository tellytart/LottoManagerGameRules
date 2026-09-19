# Changelog

All notable changes to the game rules are documented here. Entries name the game, what changed, and the `effectiveFrom` date the change applies to.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). The file format itself is versioned by the folder name (`v1/`); this log tracks the rules inside it.

## [Unreleased]

### Added

- `.github/workflows/validate.yml` (job **Validate**), the pull-request gate, replacing the stopgap `tests.yml`: on `pull_request` only, read-only token, actions pinned to commit SHAs, Python 3.12. It checks out the pull request and the base commit, runs the schema check, the checksum check and `validate.py` with the base copy of the rules file, then the unit tests. The rules-file steps are skipped, with a notice, until `v1/game-rules.json` exists, and fail a pull request that deletes it once it does.
- `scripts/check_schema.py FILE`: checks a rules file against the JSON Schema (`REJECT schema <where>: <message>`, exit 1; exit 2 if it could not run), reading the file with `validate.py`'s parser so both agree on what valid JSON is. Tests in `tests/test_check_schema.py`.
- `scripts/validate.py FILE [--base OLDER]`: every rejection and degrade rule of the format spec, with a stable machine-readable reason code per rule (`REJECT <code> <where>: <message>`, exit 1; exit 2 if it could not run). `--base` also rejects a file in which a rule set already in the older copy changed or vanished. Standard library only.
- Shared sample files: `tests/valid/` (minimal, four games, unknown colour, unknown field, unsupported-currency Game, same-date correction, and a base/new pair for "held rule sets unchanged"), `tests/invalid/` (one sample per rule, some with variants, and base/changed pairs for the held-rule-set rule) with a `tests/invalid/README.md`, and `tests/expected.json` mapping each invalid sample to its reason code.
- `tests/test_validate.py`: runs `validate.py` on every sample and asserts accept/reject and the exact reason code.
- `.gitignore` for Python bytecode, `.DS_Store` and virtual environments.
- `schema/game-rules-v1.schema.json`: JSON Schema (2020-12) for the rules file's shape: games, ball schemes, rule sets, draws, number sets, prize tiers (fixed, variable, instalments), raffle. Unknown extra fields are allowed; unknown prize or extra kinds are rejected.
- `scripts/seal.py`: writes the raw-bytes SHA-256 checksum on the file's last line, and `--check` verifies it (fails on a missing, malformed or wrong checksum and on CRLF line endings). Standard library only.
- Unit tests for both (`tests/test_seal.py`, `tests/test_schema.py`) and `requirements.txt` pinning `jsonschema`.
- Repository skeleton: `.gitattributes` (LF endings for `*.json`), `README.md`, `CHECKLIST.md`, and empty `v1/`, `schema/`, `scripts/`, `tests/valid/`, `tests/invalid/` and `.github/workflows/` folders.
- `AGENTS.md` (instructions for AI agents working in this repo) and `Journal.md` (a running notebook of decisions and gotchas).
