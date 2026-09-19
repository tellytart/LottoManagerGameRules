# Monthly check

Do this once a month, and again before any date the operator has announced a change for. The rules move (Lotto gained a second Round on 7 June 2026), so the file is only as good as the last check.

## 1. Read the official pages

Compare each page with `v1/game-rules.json` for the game it covers. Sources are all primary (Allwyn / The National Lottery); editions and dates below are from when the rules were first researched, so a newer edition is the thing to look for.

| Source | URL | What to check | Edition when researched |
|---|---|---|---|
| Lotto procedures | https://www.national-lottery.co.uk/games/lotto/game-procedures | price, ranges, Rounds, prize tiers | Edition 22, effective 7 June 2026 |
| EuroMillions procedures | https://www.national-lottery.co.uk/games/euromillions/game-procedures | price, ranges, prize tiers | Edition 24a, effective 28 July 2025 |
| Thunderball procedures | https://www.national-lottery.co.uk/games/thunderball/game-procedures | price, ranges, prize tiers | Edition 14, effective 1 February 2024 |
| Set For Life procedures | https://www.national-lottery.co.uk/games/set-for-life/game-procedures | price, ranges, prize tiers | Edition 4, effective 1 February 2024 |
| Set For Life game specific rules | https://www.national-lottery.co.uk/games/set-for-life/game-specific-rules | instalment prizes | Edition 2a, effective 28 July 2025 |
| About pages | https://www.national-lottery.co.uk/games/lotto/about-lotto, `/games/euromillions/about-euromillions`, `/games/thunderball/about-thunderball`, `/games/set-for-life/about-set-for-life` | draw days, live-draw times, cut-off wording | n/a |
| Service guide | https://www.national-lottery.co.uk/service-guide | online cut-off, syndicate manager limits | n/a |
| How to claim | https://www.national-lottery.co.uk/results/how-to-claim | claim window (`claimDays`) and routes | n/a |

Known gaps from the first research (not verified then, so worth a look): the retailer cut-off time, exact draw machine times (the pages give live-show times), and whether Lotto's per-tier odds are per Round or per Draw. Do not hard-code Lotto's starting jackpot; the procedures give only a percentage of sales plus rollovers.

## 2. If nothing changed

Bump `checkedOn` to today's date, run the checks below, add a `CHANGELOG.md` line ("checked, no change"), open a pull request.

## 3. If something changed

1. Never edit a published rule set. Add a new one: a new `effectiveFrom` (the first draw date it applies to), or the same `effectiveFrom` with a higher revision for a correction. The id is `<game>-<effectiveFrom>-r<revision>`.
2. Where the operator gave notice, publish at least a week before the change takes effect so devices fetch it in time.
3. Bump `checkedOn`.
4. Add a `CHANGELOG.md` entry naming the game, the change and the `effectiveFrom` date.

## 4. Check and publish

1. `python3 scripts/seal.py v1/game-rules.json` to write the checksum on the last line (`--check` verifies it).
2. `python3 scripts/validate.py v1/game-rules.json --base <copy of the file on main>` to run the full validation rules, including "no already-published rule set changed" (`git show main:v1/game-rules.json > /tmp/base.json` makes the copy).
3. `cp v1/game-rules.json tests/valid/current-game-rules.json`, so the shared sample stays identical (a unit test fails if it is not), then `python3 -m unittest discover -s tests`.
4. Open a pull request; the validation workflow must pass. Merge with squash or rebase (the branch keeps a linear history).
