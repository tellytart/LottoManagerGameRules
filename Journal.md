# LottoManagerGameRules Journal

A living, plain-English notebook for this repo, written for a smart friend rather than a textbook. It grows as the repo does. Public repo, so nothing private goes in here.

## 1. The Big Picture

Imagine the LottoManager app as a shop that needs today's price list on the door. Lottery prices, draw days and prize tiers do change (Lotto gained a second Round on 7 June 2026), and nobody wants to wait for an App Store release to update a sign. This repo is that price list: one small JSON file the app fetches over the internet, plus the tooling that stops a typo from ever reaching the door.

Right now the repo has the tooling (schema, seal script, validator, sample files) the pull-request gate (CI) and the first rules file.

## 2. Architecture Deep Dive

There is almost no architecture, which is the point. Think of a noticeboard with a strict clerk:

- **The file** (`v1/game-rules.json`) is the notice. Games, each with frozen, versioned *rule sets*.
- **The seal** (`scripts/seal.py`) is a wax stamp: a SHA-256 checksum on the file's last line, so a half-downloaded file is rejected instead of trusted.
- **The clerk** (`scripts/validate.py`, with CI to come) refuses any notice that breaks the rules, including quietly editing one already published.
- **`checkedOn`** is a "last verified" sticker, bumped every month even when nothing changed.

## 3. The Codebase Map

`README.md` has the layout table. In short: `v1/` the file, `schema/` its JSON Schema, `scripts/` the seal and validator, `tests/valid` and `tests/invalid` sample files shared with the app, `.github/workflows/` CI, `CHECKLIST.md` the monthly check. `v1/game-rules.json` is the notice itself. `.github/workflows/validate.yml` is the CI gate.

## 4. Tech Stack & Why

- **A static JSON file on GitHub**, not a server: nothing to run, nothing to patch, nothing that can see users. The app sends only an ordinary HTTPS request.
- **Python scripts** for the seal and validator: the same rules run locally and in CI, and Python is easy to read for a check this small.
- **Major version in the path (`v1/`)**: a breaking format change adds `v2/` and old apps keep getting ordinary rule updates.

## 5. The Journey

### 2026-09-19: The first rules file

- **Decision (Richard):** this repo has no version number, version file, build number or release tags. The rules are versioned inside the file by rule set (`effectiveFrom` date plus revision on that date), so a repo-level version would say nothing extra. Written into AGENTS.md and README.
- Wrote `v1/game-rules.json` with the four games and sealed it. It passes `validate.py`, the schema check and CI, and the first time the CI's rules-file steps run for real is on this change.
- **Gotcha (the ticket was wrong):** issue #5 said Set For Life has "seven fixed tiers plus two instalments" (nine). The research's own table lists eight rows: six fixed and two instalments. Rather than guess, the odds settled it: the published "any prize" figure (1 in 12.4) is reproduced exactly by summing the odds of those eight tiers, and a ninth tier (say "1 + Life Ball") would make it about 1 in 8.5. The file has eight tiers. The same check gave 1 in 13 for EuroMillions' 13 tiers and 1 in 4.9 for Lotto over both Rounds. Thunderball's nine tiers give 1 in 12.4 where the research says 1 in 13; every one of its tiers' own odds matches the research, so that looks like rounding in the note, but it is worth a glance when Richard reads the official page.
- **Decision:** `effectiveFrom` is the effective date of the operator's current edition (EuroMillions 2025-07-28, Thunderball 2024-02-01), and for Set For Life the later of its two documents (procedures 2024-02-01, instalment rules 2025-07-28), because the instalment prizes only exist in the file as the newer edition describes them. A draw on or after that date uses the set, which is all that matters today.
- **Decision:** tier lists run highest first, in the order the operator's tables give them, because a line takes the first tier it satisfies. For EuroMillions that order is by rarity, not prize (e.g. `4 + 1` before `3 + 2` before `4`).
- **Decision:** ball colours for Lotto follow the app's existing scheme; for the other three games the sources give none, so each number set has one colour (blue numbers, gold extra ball; purple for Set For Life). The app uses its own colours, so this is cosmetic.
- **Decision:** the real file is copied to `tests/valid/current-game-rules.json` as the ticket asked (so the app's tests run against it), and a test fails if the copy drifts. The price is one extra `cp` at every monthly check (in `CHECKLIST.md`).
- The file was generated once by a throwaway script and is now hand-maintained: edit, run `seal.py`, refresh the copy.

### 2026-09-19: The CI workflow and the pull-request gate

- Added `.github/workflows/validate.yml` and replaced the stopgap `tests.yml` with it (two workflows running the same unit tests would just be noise). Think of it as the clerk's desk at the front door: nothing reaches `main` without passing the same checks you can run by hand.
- **Decision:** a new `scripts/check_schema.py` runs the schema check, rather than an inline `python -c` in the workflow, so it is testable and runs the same locally. It parses the file with `validate.py`'s own parser, so both scripts agree on what valid JSON is.
- **Gotcha:** `v1/game-rules.json` does not exist until issue #5, so the workflow skips the rules-file steps with a notice instead of failing on a missing file. Once the file is on the base branch, a pull request that deletes it fails (otherwise deleting the file would be a way past every check).
- **Gotcha:** the workflow runs the pull request's *own* `scripts/`, so a pull request could weaken the check that judges it. Only the rules file is compared with the base branch. The defence is human: read changes to `scripts/`, `schema/`, `tests/` and `.github/` before merging (written in README and AGENTS.md).
- **Gotcha (found in review):** the event's `pull_request.base.sha` is fixed when the pull request is opened or pushed to, but GitHub's merge commit is rebuilt against the *current* `main`. Using `base.sha` for the base checkout could therefore miss a rules file that landed on `main` in between, and silently skip the "held rule sets unchanged" check. The base is now the merge commit's first parent (`HEAD^1`), so both checkouts always agree.
- **Gotcha:** the job's name (`Validate`) is what the ruleset lists as the required check, and it can only be picked after the workflow has run once. Renaming the job silently un-requires it.
- Still to do by Richard, after the first pull request has run it: add **Validate** as a required status check in the "Updates to main" ruleset and turn on "up to date before merging". Then a deliberate bad pull request (wrong checksum) is shown failing and closed.

### 2026-09-19: The validator and the shared samples

- Added `scripts/validate.py` and the sample files. Think of the samples as the clerk's exam paper: one deliberately broken notice per rule, each with the answer (the reason code) written in `tests/expected.json`. The app's own validator sits the same exam, so the two cannot quietly disagree.
- **Decision:** the validator hand-checks the file's shape instead of using `jsonschema`, so it runs with only the standard library (like `seal.py`) and reports the *same reason codes* the app will use. The schema stays for editors, and a test checks that every valid sample also satisfies it.
- **Decision:** it lists every problem, not just the first, but each invalid sample breaks exactly one rule and the test demands exactly that one code, so a check that over-reports fails the tests.
- **Decision (the spec was silent):** a prize tier "cannot match" if it needs more main numbers than are drawn, more of an extra set than it draws, a Bonus Ball the game does not have, or a Bonus Ball together with *all* the main numbers (nothing is left to match it with). Shadowed tiers are not checked. Written up in `tests/invalid/README.md`; the app's spec still needs the same words so both sides agree.
- **Gotcha:** the spec says `effectiveFrom` must be "strictly rising" *and* that a correction keeps the same date with a higher revision. Both are true only if rule sets are ordered by (date, revision), so that is the rule.
- **Gotcha:** Python's `True == 1` and `200 == 200.0`, so the amount check refuses booleans and any decimal point (`200.0` is rejected), and the held-rule-set comparison uses a canonical text form so `200` and `200.0` count as different.
- **Gotcha:** a Game in an unsupported currency is skipped by the app, but the validator still checks it fully, so a typo in it cannot hide until the day the app supports that currency.
- **Gotcha (found in review):** a required member set to `null` looked "present" to the first version and was accepted; `null` now counts as missing. Likewise an object with the same key twice is refused, because Python keeps the last one and another parser might keep the first.
- **Gotcha:** JSON does not allow `NaN`, but Python's parser accepts it, so the parser is told to refuse it.
- Samples are generated once and then hand-maintained: edit, then run `seal.py` on the file. The real games' numbers in them are illustrative; issue #5 supplies the real file.

### 2026-09-19: Schema and seal script

- Added the JSON Schema and `scripts/seal.py`. Think of the seal as the wax stamp on the notice: it hashes every byte *above* the checksum line, so the stamp cannot be part of what it stamps.
- **Decision:** the schema checks shape only and allows unknown extra fields, but rejects an unknown prize or extra *kind*, because a kind we do not know would change how prizes are worked out. Cross-file rules (unique ids, rising dates, real time zones, tiers that can match) are left to `validate.py`, since JSON Schema cannot express them.
- **Decision:** `seal.py` refuses to write anything that would not be valid JSON, and runs its own `check` on its output, so it cannot produce a file the app would reject. It writes through a temp file and a rename so a crash cannot leave a half-written rules file.
- **Gotcha:** the seal has to reproduce exactly in Swift. The tests carry one known-answer checksum computed with `shasum`, independently of the script, and the app's tests should reuse it.
- **Gotcha:** the schema tests skip themselves if `jsonschema` is missing, which is friendly locally and dangerous in CI, so the workflow fails loudly if it is not installed.
- **Decision:** actions in the workflow are pinned to full commit SHAs, not tags, and it uses `pull_request` (never `pull_request_target`) with a read-only token.
- Added a minimal `Tests` workflow so pull requests get a status check. It is a stopgap: the CI issue builds the full validation workflow.

### 2026-09-19: Bootstrap

- Got the first commit ready for an empty repo. An empty repo has no `main`, so a branch protection rule that demands a pull request cannot be satisfied for the very first commit. Richard disabled the ruleset to allow it and re-enables it afterwards.
- **Gotcha:** the checksum covers raw bytes, so line endings matter. `.gitattributes` forces LF on `*.json` so a checkout on another machine cannot silently change the bytes and make every fetch fail.
- **Decision:** no licence yet. Until one is added all rights are reserved, which is easy to relax later and hard to take back.
- **Gotcha:** the ruleset requires a linear history, so merges here must be squash or rebase.
- **Lesson from review:** a first commit still needs the project's own housekeeping files (agent instructions, Journal, changelog), and a README should not describe protections that are not switched on yet.

## 6. Engineer's Wisdom

- Make the risky thing hard: a published rule set is never edited, only superseded.
- Validate in one place and share the test files with the consumer, so two implementations cannot drift apart.
- Say what is true today, not what is planned.

## 7. If I Were Starting Over...

Too early to say. Revisit after the first rules file is published.
