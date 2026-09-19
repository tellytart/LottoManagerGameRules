# AGENTS.md

Instructions for AI agents working in this repository.

## What this repo is

`LottoManagerGameRules` is a small **public** repo holding the game rules the LottoManager app fetches: one JSON file, `v1/game-rules.json`, plus the schema, scripts, sample files and CI that keep it valid. It carries facts about lottery games (prices, draw days and times, ball ranges, Rounds, prize tiers), never behaviour and never user data. The app lives in a separate, private repo (`tellytart/LottoManager`); the format is specified there in `docs/game-rules-file.md` and decided in its ADRs 0006 and 0008. Read those first if you can; if you cannot, `README.md` and `CHECKLIST.md` here are enough to start.

## Rules that must not be broken

- **Bytes matter.** The app checks a SHA-256 over the raw bytes of `v1/game-rules.json` (everything before its final `"checksum"` line). Never re-format, re-serialise or re-indent the file by hand or with a JSON tool; change it only through `scripts/seal.py` (`python3 scripts/seal.py v1/game-rules.json`; `--check` verifies). `.gitattributes` forces LF endings on `*.json` for the same reason.
- **A published rule set is never edited.** A correction is a new rule set (later `effectiveFrom`, or the same one with a higher revision). Ids look like `<game>-<effectiveFrom>-r<revision>`.
- **No version number or version file.** This repo is not versioned like an app: no `Version.xcconfig`, no semantic version, no build number, no release tags, and nothing to bump on a merge. The rules are versioned inside the file, by rule set: `effectiveFrom` date plus revision number on that date (ids look like `<game>-<effectiveFrom>-r<revision>`). The folder name (`v1/`) is the *format's* major version, not the rules'. The `CHANGELOG.md` `[Unreleased]` heading stays as it is; entries name the game and `effectiveFrom` date instead of a release number. This overrides any general "bump the version on every merge" habit or instruction.
- **Data only.** No executable content, no URLs the app should follow, nothing about users.
- **The repo is public.** Nothing private goes in files, issues, commit messages or the Journal: no credentials, no personal details, nothing from the private app repo beyond what the README already says.

## Workflow

- Work on a feature branch and open a pull request; never commit straight to `main` (the first bootstrap commit is the one exception, because an empty repo has no `main` to branch from).
- `main` is meant to keep a linear history: merge by **squash** or **rebase**, not a merge commit. Never rewrite history.
- Commit messages: a summary line plus a body that explains *why*.
- Changing repo settings, rulesets or Actions permissions needs Richard's explicit approval.
- Keep `CHANGELOG.md` current (Keep a Changelog format; rule changes name the game and the `effectiveFrom` date) and add to `Journal.md` when you learn something or hit a gotcha.

## Layout

See the table in `README.md`. Files under `scripts/`, `schema/`, `tests/` and `.github/workflows/` run in CI on a pull request's own copy, so read any change to them carefully before merging. The workflow's job is named `Validate`: that name is the required status check in the `main` ruleset, so do not rename it without telling Richard. Sample files in `tests/valid/` and `tests/invalid/` are shared with the app's own validator: change them in step with the app.

## Tests

`python3 -m pip install -r requirements.txt` once, then `python3 -m unittest discover -s tests -v`. Run them before every pull request; the `Validate` workflow runs the same thing, after the schema, checksum and `validate.py` checks on `v1/game-rules.json`.

## Monthly check

Follow `CHECKLIST.md`. Bump `checkedOn` even when nothing changed. After any change to `v1/game-rules.json`, re-seal it and refresh its copy in `tests/valid/` (a test checks they match).
