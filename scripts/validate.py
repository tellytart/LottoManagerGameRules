#!/usr/bin/env python3
"""Check a game rules file against every validation rule of the format spec.

Usage:
    validate.py FILE                   check FILE on its own
    validate.py FILE --base OLDER      also check that no rule set already in OLDER changed

Exit status:
    0   the file is accepted ("OK <file>" is printed)
    1   the file is rejected: one line per finding is printed to stdout, in the form

            REJECT <reason-code> <where>: <message>

        The reason code is a stable, machine-readable word (the list is below and in
        tests/invalid/README.md). `<where>` is a path into the file such as
        `games[0].ruleSets[1].price`. Every finding is listed, not just the first.
    2   this script could not run: unreadable FILE or --base, a --base that is not a rules
        file, or no time zone database on this machine. Nothing is said about the file.

Reason codes (the file is rejected whole, ADR 0006):
    invalid-json                 not valid JSON (this includes an object with the same key twice)
    unknown-schema-version       `schemaVersion` is not 1 (nothing else is checked)
    malformed-structure          a required member is missing or null, or has the wrong type or kind
    checksum-missing             no `checksum` member
    checksum-wrong               the checksum line is malformed or does not match the bytes
    duplicate-id                 two Games, or two rule sets, share an id
    bad-id                       an id is not in the id format (a rule set's must be
                                 `<game id>-<effectiveFrom>-r<revision>`)
    bad-amount                   a price or prize amount is not a whole number >= 0 of minor units
    min-above-max                a number set's `min` is above its `max`
    count-above-range            a number set draws more numbers than its range holds
    tier-cannot-match            a prize tier no line could ever match
    empty-tier-list              a rule set has no prize tiers
    unknown-extra-set            a tier names an extra number set the game does not have
    bad-date                     not a real YYYY-MM-DD calendar date
    bad-time                     not an HH:mm time
    bad-weekday                  not one of mon..sun
    bad-timezone                 not a time zone the IANA database knows
    effective-from-not-rising    rule sets are not in strictly rising (effectiveFrom, revision) order
    held-rule-set-changed        (with --base) a rule set in the older file changed or vanished

Accepted, not rejected ("degrade" rules): an unknown colour name, an unknown extra field, and a
Game in a currency the app does not support (it is skipped by the app, but still checked here
so a typo in it cannot hide).

Only the Python standard library is used. The checksum comes from seal.py, beside this file.
"""
import argparse
import datetime
import functools
import json
import re
import sys
import zoneinfo
from pathlib import Path

# seal.py sits beside this script; put this folder on the import path so it is found
# whether we are run as a script or imported by a test.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import seal  # noqa: E402

SUPPORTED_SCHEMA_VERSION = 1
WEEKDAYS = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}

SLUG = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")  # a Game id or a prize tier id
DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
TIME = re.compile(r"([01][0-9]|2[0-3]):[0-5][0-9]")
CURRENCY = re.compile(r"[A-Z]{3}")
REVISION = re.compile(r"[1-9][0-9]*")


class SetupError(Exception):
    """The script cannot do its job (as opposed to the file being bad). Exit status 2."""


class Findings:
    """Collects rejections as (code, where, message) so every problem is reported."""

    def __init__(self):
        self.items = []

    def add(self, code, where, message):
        self.items.append((code, where, message))


# ---------------------------------------------------------------- small type helpers
def is_int(value):
    """A JSON whole number. Python treats True/False as ints, and JSON's `2.0` is a float: neither counts."""
    return isinstance(value, int) and not isinstance(value, bool)


def is_object(value):
    """A JSON object (Python dict)."""
    return isinstance(value, dict)


def is_text(value):
    """A JSON string."""
    return isinstance(value, str)


def canonical(value):
    """A comparable text form of parsed JSON: key order and spacing do not matter, but 200 and 200.0 differ."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


@functools.lru_cache(maxsize=None)
def known_timezone(name):
    """True if `name` is an IANA time zone id on this machine's time zone database."""
    try:
        zoneinfo.ZoneInfo(name)
        return True
    except (zoneinfo.ZoneInfoNotFoundError, ValueError, OSError, TypeError):
        # Not found, a malformed key (e.g. "../x"), or a folder rather than a zone.
        # If the machine has no zone database at all, every name would look wrong: say so.
        if not zoneinfo.available_timezones():
            raise SetupError("no time zone database found on this machine (try: python3 -m pip install tzdata)")
        return False


def real_date(value):
    """True for a real calendar date written exactly YYYY-MM-DD."""
    if not is_text(value) or not DATE.fullmatch(value):
        return False
    try:
        datetime.date(int(value[:4]), int(value[5:7]), int(value[8:10]))
        return True
    except ValueError:  # e.g. 2026-02-30
        return False


# ---------------------------------------------------------------- field checkers
class Checker:
    """Checks one document and records what it finds. One instance per file."""

    def __init__(self):
        self.findings = Findings()
        self.game_ids = set()
        self.rule_set_ids = set()

    # Shorthands -------------------------------------------------------------
    def add(self, code, where, message):
        self.findings.add(code, where, message)

    def malformed(self, where, message):
        self.add("malformed-structure", where, message)

    def require(self, obj, key, where):
        """The member `key` of `obj`, or None after recording it as missing. A member that is
        present but null counts as missing: no required member may be null."""
        if obj.get(key) is None:
            self.malformed(f"{where}.{key}", "required member is missing (or null)")
            return None
        return obj[key]

    def non_empty_text(self, value, where):
        """Record a malformed-structure finding unless `value` is text with something in it."""
        if not (is_text(value) and value):
            self.malformed(where, "must be non-empty text")

    def whole_number(self, value, where):
        """A whole number of at least 0. Returns True if fine, else records it and returns False."""
        if is_int(value) and value >= 0:
            return True
        self.malformed(where, "must be a whole number of at least 0")
        return False

    def date(self, value, where):
        """Record a bad-date finding unless `value` is a real YYYY-MM-DD date. Returns True if fine."""
        if real_date(value):
            return True
        self.add("bad-date", where, f"{value!r} is not a real date written YYYY-MM-DD")
        return False

    def amount(self, value, where):
        """Record a bad-amount finding unless `value` is a whole number >= 0 (minor units)."""
        if is_int(value) and value >= 0:
            return True
        self.add("bad-amount", where, f"{value!r} is not a whole non-negative number of minor units")
        return False

    def count(self, value, where):
        """A count (>= 1). Returns the value if fine, else None after recording it."""
        if is_int(value) and value >= 1:
            return value
        self.malformed(where, f"{value!r} is not a whole number of at least 1")
        return None

    # Whole document ---------------------------------------------------------
    def check_document(self, doc):
        """Everything except the byte checksum (done first, on the raw bytes, by `validate`)."""
        checked_on = self.require(doc, "checkedOn", "$")
        if checked_on is not None:
            self.date(checked_on, "checkedOn")

        games = self.require(doc, "games", "$")
        if games is None:
            return
        if not isinstance(games, list) or not games:
            self.malformed("games", "must be a non-empty list of Games")
            return
        for index, game in enumerate(games):
            self.check_game(game, f"games[{index}]")

    def check_game(self, game, where):
        """Check one Game and all its rule sets, and that rule sets are listed in rising order."""
        if not is_object(game):
            self.malformed(where, "a Game must be an object")
            return

        game_id = self.require(game, "id", where)
        if game_id is not None:
            if not is_text(game_id):
                self.malformed(f"{where}.id", "must be text")
                game_id = None
            else:
                if not SLUG.fullmatch(game_id):
                    self.add("bad-id", f"{where}.id", f"{game_id!r} is not lowercase words joined by hyphens")
                if game_id in self.game_ids:
                    self.add("duplicate-id", f"{where}.id", f"Game id {game_id!r} is used more than once")
                self.game_ids.add(game_id)

        name = self.require(game, "name", where)
        if name is not None:
            self.non_empty_text(name, f"{where}.name")

        currency = self.require(game, "currency", where)
        if currency is not None and not (is_text(currency) and CURRENCY.fullmatch(currency)):
            self.malformed(f"{where}.currency", "must be a three-letter ISO 4217 code such as GBP")
        # A Game in a currency other than GBP is skipped by the app but is still checked in full.

        timezone = self.require(game, "timezone", where)
        if timezone is not None and not (is_text(timezone) and known_timezone(timezone)):
            self.add("bad-timezone", f"{where}.timezone", f"{timezone!r} is not an IANA time zone")

        if game.get("endsAfter") is not None:
            self.date(game["endsAfter"], f"{where}.endsAfter")

        self.check_ball_schemes(self.require(game, "ballSchemes", where), f"{where}.ballSchemes")

        rule_sets = self.require(game, "ruleSets", where)
        if rule_sets is None:
            return
        if not isinstance(rule_sets, list) or not rule_sets:
            self.malformed(f"{where}.ruleSets", "must be a non-empty list of rule sets")
            return

        previous_key = None  # (effectiveFrom, revision) of the rule set listed just before
        for index, rule_set in enumerate(rule_sets):
            key = self.check_rule_set(game_id, rule_set, f"{where}.ruleSets[{index}]")
            if key is None:
                continue
            # Equal keys are the same id twice, already reported as duplicate-id.
            if previous_key is not None and key < previous_key:
                self.add("effective-from-not-rising", f"{where}.ruleSets[{index}]",
                         f"{rule_set['id']!r} comes after a later rule set; rule sets must be listed with "
                         "effectiveFrom rising (a correction keeps the date and raises the revision)")
            previous_key = key

    def check_ball_schemes(self, schemes, where):
        """Ball colour ranges. Colour names are not checked: an unknown one just shows grey."""
        if schemes is None:
            return
        if not is_object(schemes) or "main" not in schemes:
            self.malformed(where, "must be an object with at least a 'main' list")
            return
        for set_name, ranges in schemes.items():
            if not isinstance(ranges, list) or not ranges:
                self.malformed(f"{where}.{set_name}", "must be a non-empty list of colour ranges")
                continue
            for index, entry in enumerate(ranges):
                here = f"{where}.{set_name}[{index}]"
                if not is_object(entry):
                    self.malformed(here, "a colour range must be an object")
                    continue
                for member in ("from", "to"):
                    value = self.require(entry, member, here)
                    if value is not None:
                        self.whole_number(value, f"{here}.{member}")
                color = self.require(entry, "color", here)
                if color is not None and not is_text(color):
                    self.malformed(f"{here}.color", "must be text")

    # Rule sets --------------------------------------------------------------
    def check_rule_set(self, game_id, rule_set, where):
        """Check one rule set. Returns its (effectiveFrom, revision) sort key when the id and
        date are usable, so the caller can check the ordering; otherwise None."""
        if not is_object(rule_set):
            self.malformed(where, "a rule set must be an object")
            return None

        effective_from = self.require(rule_set, "effectiveFrom", where)
        date_ok = effective_from is not None and self.date(effective_from, f"{where}.effectiveFrom")

        key = self.check_rule_set_id(game_id, rule_set, effective_from, date_ok, where)

        price = self.require(rule_set, "price", where)
        if price is not None:
            self.amount(price, f"{where}.price")
        rounds = self.require(rule_set, "rounds", where)
        if rounds is not None:
            self.count(rounds, f"{where}.rounds")
        if "claimDays" in rule_set:
            self.count(rule_set["claimDays"], f"{where}.claimDays")

        self.check_draws(self.require(rule_set, "draws", where), f"{where}.draws")
        numbers = self.check_numbers(self.require(rule_set, "numbers", where), f"{where}.numbers")
        self.check_tiers(self.require(rule_set, "tiers", where), numbers, f"{where}.tiers")
        self.check_raffle(rule_set.get("raffle"), f"{where}.raffle")
        return key

    def check_rule_set_id(self, game_id, rule_set, effective_from, date_ok, where):
        """The id must be `<game id>-<effectiveFrom>-r<revision>` and unique in the file."""
        rule_set_id = self.require(rule_set, "id", where)
        if rule_set_id is None:
            return None
        if not is_text(rule_set_id):
            self.malformed(f"{where}.id", "must be text")
            return None

        if rule_set_id in self.rule_set_ids:
            self.add("duplicate-id", f"{where}.id", f"rule set id {rule_set_id!r} is used more than once")
        self.rule_set_ids.add(rule_set_id)

        if not (is_text(game_id) and is_text(effective_from)):
            return None  # what the id should be is unknown; the missing pieces are already reported
        prefix = f"{game_id}-{effective_from}-r"
        revision = rule_set_id[len(prefix):] if rule_set_id.startswith(prefix) else None
        if revision is None or not REVISION.fullmatch(revision):
            self.add("bad-id", f"{where}.id",
                     f"{rule_set_id!r} is not <game id>-<effectiveFrom>-r<revision> "
                     f"(expected it to start {prefix!r} and end in a whole number from 1)")
            return None
        return (effective_from, int(revision)) if date_ok else None

    def check_draws(self, draws, where):
        """Each draw day needs a weekday (mon..sun) and cut-off, live and results times (HH:mm)."""
        if draws is None:
            return
        if not isinstance(draws, list) or not draws:
            self.malformed(where, "must be a non-empty list of draw days")
            return
        for index, draw in enumerate(draws):
            here = f"{where}[{index}]"
            if not is_object(draw):
                self.malformed(here, "a draw day must be an object")
                continue
            weekday = self.require(draw, "weekday", here)
            if weekday is not None and not (is_text(weekday) and weekday in WEEKDAYS):
                self.add("bad-weekday", f"{here}.weekday", f"{weekday!r} is not one of mon, tue, wed, thu, fri, sat, sun")
            for member in ("cutOff", "live", "results"):
                value = self.require(draw, member, here)
                if value is not None and not (is_text(value) and TIME.fullmatch(value)):
                    self.add("bad-time", f"{here}.{member}", f"{value!r} is not a time written HH:mm (00:00 to 23:59)")

    def check_raffle(self, raffle, where):
        """A raffle is null (none) or {"name": text, "everyDraw": true/false}."""
        if raffle is None:
            return
        if not is_object(raffle):
            self.malformed(where, "must be null or an object")
            return
        name = self.require(raffle, "name", where)
        if name is not None:
            self.non_empty_text(name, f"{where}.name")
        every_draw = self.require(raffle, "everyDraw", where)
        if every_draw is not None and not isinstance(every_draw, bool):
            self.malformed(f"{where}.everyDraw", "must be true or false")

    # Numbers ----------------------------------------------------------------
    def check_number_set(self, number_set, where, need_name=False):
        """Check a set of numbers drawn from min..max. Returns (count, size of the range), or None
        when the set is unusable. Reports min above max, and a count larger than the range."""
        ok = True
        values = {}
        for member in ("count", "min", "max"):
            value = self.require(number_set, member, where)
            if value is None:
                ok = False
            elif member == "count" and self.count(value, f"{where}.count") is None:
                ok = False
            elif member != "count" and not self.whole_number(value, f"{where}.{member}"):
                ok = False
            else:
                values[member] = value
        if need_name:
            name = self.require(number_set, "name", where)
            if name is not None:
                self.non_empty_text(name, f"{where}.name")
        if not ok:
            return None
        if values["min"] > values["max"]:
            self.add("min-above-max", where, f"min {values['min']} is above max {values['max']}")
            return None
        size = values["max"] - values["min"] + 1
        if values["count"] > size:
            self.add("count-above-range", where,
                     f"draws {values['count']} numbers from a range of only {size} ({values['min']} to {values['max']})")
        return values["count"], size

    def check_numbers(self, numbers, where):
        """Returns what the tiers need to know: {"main": count or None, "bonus": bonus ball count,
        "sets": {extra set name: count}}, or None if `numbers` is unusable."""
        if numbers is None:
            return None
        if not is_object(numbers):
            self.malformed(where, "must be an object")
            return None

        info = {"main": None, "bonus": 0, "sets": {}}
        main = self.require(numbers, "main", where)
        main_size = None
        if main is not None:
            if not is_object(main):
                self.malformed(f"{where}.main", "must be an object")
            else:
                checked = self.check_number_set(main, f"{where}.main")
                if checked:
                    main_size = checked[1]
                # The count is trusted for tier checks even if the range is broken (min above max),
                # so one mistake does not also make every tier look wrong.
                if is_int(main.get("count")) and main["count"] >= 1:
                    info["main"] = main["count"]

        extras = numbers.get("extras", [])
        if not isinstance(extras, list):
            self.malformed(f"{where}.extras", "must be a list")
            return info
        for index, extra in enumerate(extras):
            here = f"{where}.extras[{index}]"
            if not is_object(extra):
                self.malformed(here, "an extra must be an object")
                continue
            kind = self.require(extra, "kind", here)
            if kind == "bonusBall":
                count = self.require(extra, "count", here)
                if count is not None and self.count(count, f"{here}.count") is not None:
                    info["bonus"] += count
            elif kind == "separateSet":
                self.check_number_set(extra, here, need_name=True)
                # Registered even if its range is broken, so tiers naming it are not called unknown.
                if is_text(extra.get("name")) and is_int(extra.get("count")) and extra["count"] >= 1:
                    info["sets"][extra["name"]] = extra["count"]
            elif kind is not None:
                self.malformed(f"{here}.kind", f"unknown extra kind {kind!r} (v1 has bonusBall and separateSet)")

        # A Bonus Ball is drawn from the main balls, so it needs room beside the main numbers.
        if info["main"] is not None and info["bonus"] and main_size is not None:
            if info["main"] + info["bonus"] > main_size:
                self.add("count-above-range", f"{where}.extras",
                         f"{info['main']} main numbers plus {info['bonus']} Bonus Ball need more balls than the "
                         f"main range holds ({main_size})")
        return info

    # Prize tiers ------------------------------------------------------------
    def check_tiers(self, tiers, numbers, where):
        """`numbers` is what check_numbers returned; tier matching is only judged when it is usable."""
        if tiers is None:
            return
        if not isinstance(tiers, list):
            self.malformed(where, "must be a list")
            return
        if not tiers:
            self.add("empty-tier-list", where, "a rule set needs at least one prize tier")
            return
        for index, tier in enumerate(tiers):
            self.check_tier(tier, numbers, f"{where}[{index}]")

    def check_tier(self, tier, numbers, where):
        """One prize tier: id, name, a match rule (judged against `numbers`) and a prize."""
        if not is_object(tier):
            self.malformed(where, "a prize tier must be an object")
            return
        tier_id = self.require(tier, "id", where)
        if tier_id is not None and not (is_text(tier_id) and SLUG.fullmatch(tier_id)):
            self.add("bad-id", f"{where}.id", f"{tier_id!r} is not lowercase words joined by hyphens")
        name = self.require(tier, "name", where)
        if name is not None:
            self.non_empty_text(name, f"{where}.name")

        match = self.require(tier, "match", where)
        if match is not None:
            self.check_match(match, numbers, f"{where}.match")
        prize = self.require(tier, "prize", where)
        if prize is not None:
            self.check_prize(prize, f"{where}.prize")

    def check_match(self, match, numbers, where):
        """Tier-match rules (the spec leaves them open; these are the ones we settled on):
        a tier CAN match only if a line could satisfy all of these at once.
          * match.main is at most the number of main numbers drawn;
          * each match.extras[name] is at most the count of that extra set, and the set exists
            (a name the game lacks is `unknown-extra-set`);
          * match.bonusBall true needs the game to have a Bonus Ball, and match.main to be
            below the main count (a line holding every drawn main number has none left over
            to match the bonus)."""
        if not is_object(match):
            self.malformed(where, "must be an object")
            return

        main = self.require(match, "main", where)
        main_ok = main is not None and is_int(main) and main >= 0
        if main is not None and not main_ok:
            self.malformed(f"{where}.main", "must be a whole number of at least 0")

        bonus = match.get("bonusBall", False)
        if not isinstance(bonus, bool):
            self.malformed(f"{where}.bonusBall", "must be true or false")
            bonus = False

        extras = match.get("extras", {})
        extras_ok = is_object(extras)
        if not extras_ok:
            self.malformed(f"{where}.extras", "must be an object of counts keyed by extra set name")
        else:
            for set_name, wanted in extras.items():
                if not (is_int(wanted) and wanted >= 0):
                    self.malformed(f"{where}.extras.{set_name}", "must be a whole number of at least 0")
                    extras_ok = False

        if numbers is None:
            return  # the number sets are broken and already reported; no basis to judge the tier
        if main_ok and numbers["main"] is not None:
            if main > numbers["main"]:
                self.add("tier-cannot-match", f"{where}.main",
                         f"needs {main} main numbers but only {numbers['main']} are drawn")
            elif bonus and numbers["bonus"] and main >= numbers["main"]:
                self.add("tier-cannot-match", f"{where}.bonusBall",
                         f"matching all {main} main numbers leaves none to match the Bonus Ball")
        if bonus and not numbers["bonus"]:
            self.add("tier-cannot-match", f"{where}.bonusBall", "needs a Bonus Ball but the game does not draw one")
        if extras_ok:
            for set_name, wanted in extras.items():
                if set_name not in numbers["sets"]:
                    self.add("unknown-extra-set", f"{where}.extras.{set_name}",
                             f"the game has no extra number set called {set_name!r}")
                elif wanted > numbers["sets"][set_name]:
                    self.add("tier-cannot-match", f"{where}.extras.{set_name}",
                             f"needs {wanted} matches but only {numbers['sets'][set_name]} are drawn")

    def check_prize(self, prize, where):
        """fixed: an amount. variable: nothing. instalments: an amount, a count, a spacing."""
        if not is_object(prize):
            self.malformed(where, "must be an object")
            return
        kind = self.require(prize, "kind", where)
        if kind is None:
            return
        if kind not in ("fixed", "variable", "instalments") or not is_text(kind):
            self.malformed(f"{where}.kind", f"unknown prize kind {kind!r} (v1 has fixed, variable and instalments)")
            return
        if kind in ("fixed", "instalments"):
            amount = self.require(prize, "amount", where)
            if amount is not None:
                self.amount(amount, f"{where}.amount")
        if kind == "instalments":
            for member in ("count", "everyMonths"):
                value = self.require(prize, member, where)
                if value is not None:
                    self.count(value, f"{where}.{member}")


# ---------------------------------------------------------------- whole-file entry points
def check_checksum(data, doc, findings):
    """The file must carry a checksum member, and it must match the file's raw bytes."""
    if "checksum" not in doc:
        findings.add("checksum-missing", "checksum", "the file has no checksum")
        return
    try:
        seal.check(data)
    except seal.ChecksumError as err:
        findings.add("checksum-wrong", "checksum", str(err))


def parse(data):
    """Parse the file's bytes as JSON. Raises ValueError if they are not valid JSON."""
    def refuse_constant(name):
        raise ValueError(f"{name} is not valid JSON")  # Python accepts NaN and Infinity; JSON does not

    def refuse_duplicate_keys(pairs):
        # Python keeps the last of two equal keys; another parser may keep the first, so the
        # two could read different prices from one file. Refuse the ambiguity outright.
        keys = [key for key, _ in pairs]
        for key in keys:
            if keys.count(key) > 1:
                raise ValueError(f"the key {key!r} appears twice in one object")
        return dict(pairs)

    return json.loads(data.decode("utf-8"), parse_constant=refuse_constant, object_pairs_hook=refuse_duplicate_keys)


def rule_sets_by_id(doc):
    """{rule set id: rule set} for every well-enough-formed rule set in a parsed file."""
    found = {}
    games = doc.get("games") if is_object(doc) else None
    for game in games if isinstance(games, list) else []:
        rule_sets = game.get("ruleSets") if is_object(game) else None
        for rule_set in rule_sets if isinstance(rule_sets, list) else []:
            if is_object(rule_set) and is_text(rule_set.get("id")):
                found[rule_set["id"]] = rule_set
    return found


def check_held_rule_sets(doc, base_doc, findings):
    """No rule set that was already published (in the base file) may change or disappear."""
    now = rule_sets_by_id(doc)
    for rule_set_id, old in rule_sets_by_id(base_doc).items():
        if rule_set_id not in now:
            findings.add("held-rule-set-changed", rule_set_id,
                         "this rule set is in the base file but missing here; published rule sets are never removed")
        elif canonical(now[rule_set_id]) != canonical(old):
            findings.add("held-rule-set-changed", rule_set_id,
                         "this rule set differs from the base file; a published rule set is never edited, "
                         "a correction is a new rule set (higher revision or later effectiveFrom)")


def validate(data, base_doc=None):
    """Validate a file's bytes. Returns a list of (code, where, message); empty means accepted."""
    findings = Findings()
    try:
        doc = parse(data)
    except (UnicodeDecodeError, ValueError) as err:
        findings.add("invalid-json", "$", str(err))
        return findings.items
    if not is_object(doc):
        findings.add("malformed-structure", "$", "the file must be a JSON object")
        return findings.items
    if not is_int(doc.get("schemaVersion")) or doc["schemaVersion"] != SUPPORTED_SCHEMA_VERSION:
        findings.add("unknown-schema-version", "schemaVersion",
                     f"{doc.get('schemaVersion')!r} is not a schema version this validator knows (1)")
        return findings.items  # a different version may be shaped differently: say nothing more

    check_checksum(data, doc, findings)
    checker = Checker()
    checker.check_document(doc)
    findings.items += checker.findings.items
    if base_doc is not None:
        check_held_rule_sets(doc, base_doc, findings)
    return findings.items


def read_bytes(path, what):
    """The raw bytes of a file, or a SetupError naming `what` (e.g. "base file") if unreadable."""
    try:
        return Path(path).read_bytes()
    except OSError as err:
        raise SetupError(f"cannot read {what} {path}: {err.strerror}") from err


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate a game rules file.")
    parser.add_argument("file", help="the rules file to check")
    parser.add_argument("--base", metavar="OLDER",
                        help="an older copy of the file (e.g. from the base branch): its rule sets must be unchanged")
    args = parser.parse_args(argv)  # a usage error exits with status 2

    try:
        data = read_bytes(args.file, "file")
        base_doc = None
        if args.base is not None:
            try:
                base_doc = parse(read_bytes(args.base, "base file"))
            except (UnicodeDecodeError, ValueError) as err:
                raise SetupError(f"base file {args.base} is not valid JSON: {err}") from err
            if not is_object(base_doc) or not isinstance(base_doc.get("games"), list):
                raise SetupError(f"base file {args.base} is not a game rules file (no 'games' list)")
        findings = validate(data, base_doc)
    except SetupError as err:
        print(f"validate.py: {err}", file=sys.stderr)
        return 2

    if not findings:
        print(f"OK {args.file}")
        return 0
    for code, where, message in findings:
        print(f"REJECT {code} {where}: {message}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
