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
| `v1/game-rules.json` | The file the app fetches: Lotto, EuroMillions, Thunderball and Set For Life, one current rule set each |
| `schema/game-rules-v1.schema.json` | JSON Schema for the file's shape, so editors and CI flag mistakes |
| `scripts/seal.py` | Writes (`seal.py FILE`) or verifies (`seal.py --check FILE`) the checksum on the file's last line |
| `scripts/validate.py` | The full validation rules: `validate.py FILE [--base OLDER]` exits 1 with a stable reason code per broken rule (see `tests/invalid/README.md`); `--base` also checks that no published rule set changed |
| `tests/valid/`, `tests/invalid/`, `tests/expected.json` | Sample files (`tests/valid/current-game-rules.json` is a byte-for-byte copy of the real file, kept in step by a test) (one invalid sample per rule, mapped to its reason code in `expected.json`), shared with the app's own validator so the two stay in step |
| `scripts/check_schema.py` | Checks a rules file against the JSON Schema: `check_schema.py FILE` (needs `jsonschema`) |
| `tests/test_*.py` | Unit tests for the scripts, the schema and the real rules file (`test_rules_file.py`) |
| `.github/workflows/validate.yml` | CI, the pull-request gate (job **Validate**): on every pull request, the schema check, the checksum check and `validate.py` against the base branch's copy of the rules file (skipped while `v1/game-rules.json` does not exist yet), then the unit tests |
| `CHECKLIST.md` | The monthly check |
| `CHANGELOG.md` | What changed in the rules, and when |

## Changing the rules

There is no version number or version file for this repo. The rules are versioned inside the file: each rule set has an `effectiveFrom` date and a revision number on that date. The `v1` in the path is the *format's* major version.

- A published rule set is never edited. A correction is a new rule set: a later `effectiveFrom`, or the same one with a higher revision.
- Changes go in by pull request. The plan is for `main` to be protected and keep a **linear history**, so merge with **squash** or **rebase**, not a merge commit.
- The file ends with a checksum line written by `scripts/seal.py` (`python3 scripts/seal.py v1/game-rules.json`), and a pull request with a wrong checksum fails the **Validate** check. That check only blocks a merge once it is listed as a required status check in the `main` ruleset (which can only be done after the workflow has run once), together with "up to date before merging"; until then it reports a result but does not enforce it.
- **Read changes to `scripts/`, `schema/`, `tests/` and `.github/` before merging them.** The workflow runs the pull request's *own* copy of them (that is how a change to a check gets tested), so a pull request can weaken the very check that is judging it. Only the rules file is compared against the base branch.
- `.gitattributes` forces LF line endings on `*.json`, because the checksum covers the raw bytes.

The format is specified in the LottoManager project's `docs/game-rules-file.md` (that repository is currently private, so the link may not open for you).

## Running the tests

```sh
python3 -m pip install -r requirements.txt   # once: the pinned jsonschema
python3 -m unittest discover -s tests -v
```

## Licence

**Undecided.** No licence has been chosen yet (decision recorded 2026-09-19), so until a licence file is added all rights are reserved and this repository may not be reused.
