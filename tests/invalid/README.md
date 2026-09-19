# Invalid sample files

Each file here breaks exactly one validation rule, and `scripts/validate.py` must reject it with exactly the reason code that `tests/expected.json` gives for it. The app's own validator (in the private LottoManager repo) is tested against these same files, so **keep the layout and names simple and stable, and change them in step with the app**.

## Layout

- **`<reason-code>.json`** is the basic sample for a rule. A rule that can be broken in more than one way also has variants named **`<reason-code>--<what-is-different>.json`** (for example `bad-amount--negative-prize.json`). The name always starts with the reason code.
- **`../expected.json`** maps each sample's file name to its reason code, and is the authority (not the file name).
- **A pair for a comparison rule.** The rule "no already-published rule set changed" needs two files: the changed file `<name>.json` and, beside it, the older copy `<name>.base.json`. Run it as `validate.py <name>.json --base <name>.base.json`. A `.base.json` file is not a sample of its own (it is not listed in `expected.json`) but is itself a valid file. Only `held-rule-set-changed*` samples come as pairs; the same file checked without `--base` is accepted.
- Every sample carries a correct checksum (except the ones that are about the checksum, and `invalid-json.json`), so the one rule it breaks is the only one it breaks. To edit a sample by hand, change it and then run `python3 scripts/seal.py tests/invalid/<file>.json`.
- The valid counterparts live in `../valid/` with the same conventions (`<name>.base.json` is the `--base` file for `<name>.json`).
- The games in the samples are shaped like the real ones but their numbers are illustrative, not the published rules.

## Reason codes

`validate.py` prints one line per finding, `REJECT <reason-code> <where>: <message>`, and exits 1. The reason code is the stable part.

| Reason code | The rule it enforces |
|---|---|
| `invalid-json` | The file is not valid JSON (an object with the same key twice counts: parsers disagree about which one wins) |
| `unknown-schema-version` | `schemaVersion` is not 1 (nothing else in the file is checked) |
| `malformed-structure` | A required member is missing or `null`, or has the wrong type, or is an unknown prize or extra `kind` |
| `checksum-missing` | There is no `checksum` member |
| `checksum-wrong` | The checksum line is malformed, or does not match the file's raw bytes |
| `duplicate-id` | Two Games, or two rule sets, have the same id |
| `bad-id` | An id is not in its format: a rule set's must be `<game id>-<effectiveFrom>-r<revision>` (revision a whole number from 1) |
| `bad-amount` | A price or prize amount is not a whole non-negative number of minor units (no decimals, not `200.0`, not text, not negative) |
| `min-above-max` | A number set's `min` is above its `max` |
| `count-above-range` | A number set draws more numbers than its range holds (a Bonus Ball is drawn from the main balls, so it counts against the main range) |
| `tier-cannot-match` | No line could ever match the tier: see "Tier-match rules" below |
| `empty-tier-list` | A rule set has no prize tiers |
| `unknown-extra-set` | A tier names an extra number set the game does not have |
| `bad-date` | A date is not a real calendar date written `YYYY-MM-DD` (`checkedOn`, `effectiveFrom`, `endsAfter`) |
| `bad-time` | A time is not `HH:mm` (`00:00` to `23:59`) |
| `bad-weekday` | A weekday is not one of `mon` `tue` `wed` `thu` `fri` `sat` `sun` |
| `bad-timezone` | A time zone is not one the IANA database knows |
| `effective-from-not-rising` | Within a Game, rule sets are not listed in strictly rising order of (`effectiveFrom`, revision) |
| `held-rule-set-changed` | With `--base`: a rule set that is in the older file changed (anywhere, including nested fields) or is missing |

## Decisions where the spec is silent

- **Tier-match rules.** A tier cannot match if `match.main` is more than the number of main numbers drawn; if a `match.extras` count is more than that extra set draws; if `bonusBall` is true and the game has no Bonus Ball; or if `bonusBall` is true and `match.main` equals the main count (a line that holds every drawn main number has none left to match the Bonus Ball with). Shadowed tiers (one an earlier tier always wins first) are not checked.
- **Rising `effectiveFrom`.** The spec says "strictly rising" and also that a correction keeps its date and raises the revision. Both hold if rule sets are ordered by (`effectiveFrom`, revision): equal dates are fine when the revision goes up. Listing a rule set with an earlier key after a later one is rejected; the same id twice is `duplicate-id`.
- **Unsupported currency.** Such a Game is skipped by the app but still fully checked here.
- **Removing a held rule set** counts as changing it.
