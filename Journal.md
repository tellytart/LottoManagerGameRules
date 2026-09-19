# LottoManagerGameRules Journal

A living, plain-English notebook for this repo, written for a smart friend rather than a textbook. It grows as the repo does. Public repo, so nothing private goes in here.

## 1. The Big Picture

Imagine the LottoManager app as a shop that needs today's price list on the door. Lottery prices, draw days and prize tiers do change (Lotto gained a second Round on 7 June 2026), and nobody wants to wait for an App Store release to update a sign. This repo is that price list: one small JSON file the app fetches over the internet, plus the tooling that stops a typo from ever reaching the door.

Right now the repo is just a skeleton. The rules file itself, the validator and the CI arrive in later steps.

## 2. Architecture Deep Dive

There is almost no architecture, which is the point. Think of a noticeboard with a strict clerk:

- **The file** (`v1/game-rules.json`) is the notice. Games, each with frozen, versioned *rule sets*.
- **The seal** (`scripts/seal.py`, later) is a wax stamp: a SHA-256 checksum on the file's last line, so a half-downloaded file is rejected instead of trusted.
- **The clerk** (`scripts/validate.py` and CI, later) refuses any notice that breaks the rules, including quietly editing one already published.
- **`checkedOn`** is a "last verified" sticker, bumped every month even when nothing changed.

## 3. The Codebase Map

`README.md` has the layout table. In short: `v1/` the file, `schema/` its JSON Schema, `scripts/` the seal and validator, `tests/valid` and `tests/invalid` sample files shared with the app, `.github/workflows/` CI, `CHECKLIST.md` the monthly check. Most of these folders are empty placeholders (`.gitkeep`) today.

## 4. Tech Stack & Why

- **A static JSON file on GitHub**, not a server: nothing to run, nothing to patch, nothing that can see users. The app sends only an ordinary HTTPS request.
- **Python scripts** for the seal and validator: the same rules run locally and in CI, and Python is easy to read for a check this small.
- **Major version in the path (`v1/`)**: a breaking format change adds `v2/` and old apps keep getting ordinary rule updates.

## 5. The Journey

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
