# LottoManagerGameRules

The game rules the LottoManager app fetches: prices, draw days and times, cut-offs, ball ranges, Rounds and prize tiers for each lottery game, as one small JSON file.

**The file:** `v1/game-rules.json` on `main`, fetched by the app from
`https://raw.githubusercontent.com/tellytart/LottoManagerGameRules/main/v1/game-rules.json`.
The `v1` is the format's major version: a breaking change to the format adds a `v2/` folder, and `v1/` keeps being updated for a while so older apps are not stranded.

**Data only, no user data.** The file holds facts about games, never behaviour, and the app sends nothing about its users when it fetches it: only an ordinary HTTPS request. The file carries a `checkedOn` date that is bumped at each monthly check, even when nothing changed, and the app shows it.

**Where the facts come from.** Official National Lottery / Allwyn game procedures and pages (listed in [CHECKLIST.md](CHECKLIST.md)). The file restates facts (a price, a draw day, the number of balls); it does not copy their text.

## Layout

| Path | What it is |
|---|---|
| `v1/game-rules.json` | The file the app fetches (added by a later change) |
| `schema/game-rules-v1.schema.json` | JSON Schema for the file's shape, so editors and CI flag mistakes |
| `scripts/seal.py` | Writes (`seal.py FILE`) or verifies (`seal.py --check FILE`) the checksum on the file's last line |
| `scripts/validate.py` | The full validation rules: `validate.py FILE [--base OLDER]` exits 1 with a stable reason code per broken rule (see `tests/invalid/README.md`); `--base` also checks that no published rule set changed |
| `tests/valid/`, `tests/invalid/`, `tests/expected.json` | Sample files (one invalid sample per rule, mapped to its reason code in `expected.json`), shared with the app's own validator so the two stay in step |
| `tests/test_*.py` | Unit tests for the scripts and the schema |
| `.github/workflows/` | CI: `tests.yml` runs the unit tests (including every sample file) on every pull request; the full validation workflow comes later |
| `CHECKLIST.md` | The monthly check |
| `CHANGELOG.md` | What changed in the rules, and when |

## Changing the rules

- A published rule set is never edited. A correction is a new rule set: a later `effectiveFrom`, or the same one with a higher revision.
- Changes go in by pull request. The plan is for `main` to be protected and keep a **linear history**, so merge with **squash** or **rebase**, not a merge commit.
- The file ends with a checksum line written by `scripts/seal.py` (`python3 scripts/seal.py v1/game-rules.json`), and a pull request with a wrong checksum will fail a validation check. The check arrives with later work; until the branch protection is switched on and that workflow has run once, nothing enforces them.
- `.gitattributes` forces LF line endings on `*.json`, because the checksum covers the raw bytes.

The format is specified in the LottoManager project's `docs/game-rules-file.md` (that repository is currently private, so the link may not open for you).

## Running the tests

```sh
python3 -m pip install -r requirements.txt   # once: the pinned jsonschema
python3 -m unittest discover -s tests -v
```

## Licence

**Undecided.** No licence has been chosen yet (decision recorded 2026-09-19), so until a licence file is added all rights are reserved and this repository may not be reused.
