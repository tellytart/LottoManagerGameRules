# Changelog

All notable changes to the game rules are documented here. Entries name the game, what changed, and the `effectiveFrom` date the change applies to.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). The file format itself is versioned by the folder name (`v1/`); this log tracks the rules inside it.

## [Unreleased]

### Changed

- The site's Terms of Use links now point at Apple's standard EULA at its current address, `https://www.apple.com/legal/internet-services/itunes/dev/stdeula/`. Apple moved it from `.../internetservices/...`, which now returns 404, so every Terms link on the site was broken.
- The site's domain is now lottomanager.richardholland.com (it moved from support.richardholland.com); the README, AGENTS.md and the stylesheet's header comment say so.
- The Support page no longer writes the support email address in its source: a small script assembles it in the browser, so bots scanning the HTML for addresses find nothing. Without JavaScript the page shows the address spelled out in words instead of a button.

### Added

- **The support site** in `docs/`, served by GitHub Pages at lottomanager.richardholland.com: a home page, the Privacy Policy (`/privacy/`), the Support page (`/support/`, an email link) and one shared `site.css` built from the app's design tokens. Terms of Use links out to Apple's standard EULA from every page. `.nojekyll` tells Pages to serve the files as they are. This does not change the rules file.
- **First rules file, `v1/game-rules.json`** (checked 2026-09-19 against the figures researched that day, see CHECKLIST.md for the sources), one current rule set per game:
  - Lotto, `lotto-2026-06-10-r1`, effective 2026-06-10: £2.00, two Rounds, Wed and Sat, Match 6 jackpot (manager types it) down to Match 2, Guaranteed Millionaire Raffle.
  - EuroMillions, `euromillions-2025-07-28-r1`, effective 2025-07-28: £2.50, Tue and Fri, 13 tiers all typed by the manager, UK Millionaire Maker raffle.
  - Thunderball, `thunderball-2024-02-01-r1`, effective 2024-02-01: £1.00, Tue, Wed, Fri and Sat, nine fixed tiers.
  - Set For Life, `set-for-life-2025-07-28-r1`, effective 2025-07-28: £1.50, Mon and Thu, eight tiers: six fixed cash and two monthly-instalment prizes (£10,000 a month for 360 and for 12 months).
- `tests/test_rules_file.py`: the real file passes `validate.py` and the seal check, has the four games, and matches its copy `tests/valid/current-game-rules.json`.
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
