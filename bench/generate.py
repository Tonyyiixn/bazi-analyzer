"""Builds the benchmark question sets (bench/data/<set>.jsonl).

- eval: the formal set. Generated once and frozen - never regenerated or
        edited; data/eval.sha256 lets runner.py refuse a modified copy.
- dev:  ~25 records per suite for debugging prompts and scoring. Disposable
        and regenerable; its charts never overlap eval's.

Three suites share a single record schema (see `record()` below):

- accuracy:     birth data in, one structural fact out (day pillar, a stem's
                Ten God, a branch's hidden stems). Run once with Claude alone
                and once with Claude + MCP tools, then compare against gold.
- stability:    the same chart asked several different ways (EN + ZH
                paraphrases, different framings) plus repeated runs of the
                canonical ask. Every variant asks for the same "core" facts,
                so a stable model returns the same core regardless of wording.
- interactions: list every branch interaction in the chart; scored with
                set-level F1 over normalized interaction keys. Each chart is
                asked twice - from birth data (end-to-end) and from the
                pillars directly (isolates interaction detection from chart
                calculation).

Gold answers come from this repo's deterministic engine, so "correct" means
"matches the engine". The engine's own conventions (e.g. any 2 of a
three-harmony trio counts as a partial three-harmony) therefore define gold.

Geocoding is stubbed with the fixed CITIES table so generation is offline and
reproducible. Charts whose pillars change anywhere within +/-BOUNDARY_MINUTES
of the true-solar birth time are rejected, so the small coordinate
differences a live geocoder introduces at eval time can't flip the gold.

Run from the repo root:  python -m bench.generate [--set dev] [--seed N]
"""
import argparse
import hashlib
import json
import random
import subprocess
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from types import SimpleNamespace

from core import time_engine
from core.time_engine import get_true_solar_time
from core.bazi_math import (
    calculate_bazi_chart, calculate_chart_ten_gods, calculate_chart_hidden_stems, STEM_ATTRIBUTES,
)
from core.bazi_interactions import find_branch_interactions
from core.bazi_strength import analyze_day_master_strength

DATA_DIR = Path(__file__).parent / "data"
SCHEMA_VERSION = 1
BOUNDARY_MINUTES = 20

# city -> (latitude, longitude). Spread across timezones and far from their
# standard meridians, so true-solar-time correction actually matters.
CITIES = {
    "Beijing": (39.9042, 116.4074),
    "Shanghai": (31.2304, 121.4737),
    "Chengdu": (30.5728, 104.0668),
    "Kunming": (25.0389, 102.7183),
    "Hong Kong": (22.3193, 114.1694),
    "Taipei": (25.0330, 121.5654),
    "Singapore": (1.3521, 103.8198),
    "Tokyo": (35.6762, 139.6503),
    "London": (51.5074, -0.1278),
    "New York": (40.7128, -74.0060),
    "Los Angeles": (34.0522, -118.2437),
    "Sydney": (-33.8688, 151.2093),
}

PILLARS = ("year", "month", "day", "hour")
BRANCH_ORDER = "子丑寅卯辰巳午未申酉戌亥"

STABILITY_REPEATS = 3

# eval is the frozen formal set: generated once, never regenerated or edited
# (data/eval.sha256 guards it). dev is small and disposable, for debugging
# prompts and scoring; its charts are kept disjoint from eval's.
# interaction_buckets: interaction-count bucket -> charts (4 means "4 or more").
SETS = {
    "eval": {"seed": 7, "id_prefix": "", "accuracy_charts": 30, "stability_charts": 10,
             "interaction_buckets": {0: 6, 1: 8, 2: 10, 3: 8, 4: 8}},
    "dev": {"seed": 11, "id_prefix": "dev-", "accuracy_charts": 8, "stability_charts": 5,
            "interaction_buckets": {0: 2, 1: 2, 2: 3, 3: 3, 4: 2}},
    # The edge suite has its own pair of sets: its gold comes from
    # bench/reference.py, not the engine (see edge_records below).
    "edge-eval": {"seed": 23, "id_prefix": "", "edge_per_category": 10},
    "edge-dev": {"seed": 21, "id_prefix": "dev-", "edge_per_category": 5},
}
FROZEN_SETS = {"eval", "edge-eval"}


def _stub_geocode(name, timeout=None):
    lat, lng = CITIES[name]
    return SimpleNamespace(latitude=lat, longitude=lng)


def _pillars_at(dt, gender):
    pillars, _ = calculate_bazi_chart(dt.year, dt.month, dt.day, dt.hour, dt.minute, gender)
    return pillars


def build_chart(birth):
    """Full engine output for one birth, or None if it sits too close to a
    pillar boundary to have an unambiguous gold answer."""
    b = birth
    tst = datetime(*get_true_solar_time(b["year"], b["month"], b["day"], b["hour"], b["minute"], b["city"]))
    pillars = _pillars_at(tst, b["gender"])
    margin = timedelta(minutes=BOUNDARY_MINUTES)
    if _pillars_at(tst - margin, b["gender"]) != pillars or _pillars_at(tst + margin, b["gender"]) != pillars:
        return None

    clock = datetime(b["year"], b["month"], b["day"], b["hour"], b["minute"])
    return {
        "pillars": pillars,
        "ten_gods": calculate_chart_ten_gods(pillars),
        "hidden_stems": calculate_chart_hidden_stems(pillars),
        "branch_interactions": find_branch_interactions(pillars),
        "strength": analyze_day_master_strength(pillars),
        "true_solar_time": tst.strftime("%Y-%m-%d %H:%M"),
        # Slice on this: a Claude-only arm that skips solar-time correction
        # can only get these charts wrong.
        "tst_changes_chart": _pillars_at(clock, b["gender"]) != pillars,
    }


def random_birth(rng):
    while True:
        start = datetime(1950, 1, 1)
        dt = start + timedelta(days=rng.randrange(365 * 60), minutes=rng.randrange(24 * 60))
        # 23:00-00:59 is where schools disagree on the day boundary (早/晚子時).
        # Check against clock time; build_chart's boundary filter covers the rest.
        if dt.hour in (23, 0):
            continue
        return {
            "year": dt.year, "month": dt.month, "day": dt.day,
            "hour": dt.hour, "minute": dt.minute,
            "gender": rng.choice(["Male", "Female"]),
            "city": rng.choice(sorted(CITIES)),
        }


def pillar_key(pillars):
    return tuple(pillars[k] for k in PILLARS)


def sample_charts(rng, exclude=frozenset()):
    """Yields (birth, chart) pairs forever, skipping boundary-ambiguous ones
    and any chart whose pillars are in `exclude`."""
    while True:
        birth = random_birth(rng)
        chart = build_chart(birth)
        if chart and pillar_key(chart["pillars"]) not in exclude:
            yield birth, chart


def birth_text(b):
    return (f"{b['gender'].lower()}, born {b['year']}-{b['month']:02d}-{b['day']:02d} "
            f"at {b['hour']:02d}:{b['minute']:02d} local clock time in {b['city']}")


def birth_text_zh(b):
    gender = "男" if b["gender"] == "Male" else "女"
    return (f"{gender}，{b['year']}年{b['month']}月{b['day']}日 {b['hour']:02d}:{b['minute']:02d}"
            f"（当地钟表时间）出生于{b['city']}")


def pillars_text(p):
    return f"Year {p['year']}, Month {p['month']}, Day {p['day']}, Hour {p['hour']}"


def interaction_key(ix):
    """Normalized, order-independent key used for F1 matching, e.g.
    "clash:子-午", "three_harmony:申-子", "punishment:午-午"."""
    branches = sorted(ix["branches"], key=BRANCH_ORDER.index)
    return f"{ix['type']}:{'-'.join(branches)}"


def record(suite, task, chart_id, birth, chart, question, answer_format, gold, **extra):
    rec = {
        "id": None,  # assigned once all records exist
        "suite": suite,
        "task": task,
        "chart_id": chart_id,
        "input_mode": "birth",
        "birth": birth,
        "pillars_given": None,
        "question": question,
        "answer_format": answer_format,
        "gold": gold,
        "group_id": None,
        "variant": None,
        "repeats": 1,
        "meta": {
            "true_solar_time": chart["true_solar_time"],
            "tst_changes_chart": chart["tst_changes_chart"],
        },
    }
    rec.update(extra)
    return rec


# ---------------------------------------------------------------- accuracy

JSON_TAIL = "End your reply with a single-line JSON object exactly of the form: "

def accuracy_records(charts, rng):
    out = []
    for chart_id, birth, chart in charts:
        p = chart["pillars"]
        who = birth_text(birth)

        out.append(record(
            "accuracy", "day_pillar", chart_id, birth, chart,
            f"For a {who}, what is the Day Pillar (日柱) of their Bazi chart?",
            JSON_TAIL + '{"day_pillar": "<stem><branch>"}',
            {"day_pillar": p["day"], "day_master": p["day"][0]},
        ))

        pillar = rng.choice(["year", "month", "hour"])
        stem = p[pillar][0]
        out.append(record(
            "accuracy", "stem_ten_god", chart_id, birth, chart,
            f"For a {who}, what Ten God (十神) is the {pillar.title()} Pillar's Heavenly Stem "
            f"relative to the Day Master?",
            JSON_TAIL + '{"stem": "<stem character>", "ten_god": "<English Ten God name>"}',
            {"pillar": pillar, "stem": stem, "ten_god": chart["ten_gods"][pillar]["stem"]},
            target={"pillar": pillar},
        ))

        pillar = rng.choice(PILLARS)
        branch = p[pillar][1]
        hidden = chart["hidden_stems"][pillar]
        out.append(record(
            "accuracy", "hidden_stems", chart_id, birth, chart,
            f"For a {who}, what hidden stems (藏干) does the {pillar.title()} Pillar's Earthly Branch "
            f"contain? For each, give its element and its Ten God relative to the Day Master.",
            JSON_TAIL + '{"branch": "<branch>", "hidden_stems": [{"stem": "<stem>", "element": '
                        '"<Wood|Fire|Earth|Metal|Water>", "qi_type": "<main|middle|residual>", '
                        '"ten_god": "<English Ten God name>"}]}  (main qi first)',
            {"pillar": pillar, "branch": branch, "hidden_stems": [
                {**h, "element": STEM_ATTRIBUTES[h["stem"]]["element"]} for h in hidden
            ]},
            target={"pillar": pillar},
        ))
    return out


# ---------------------------------------------------------------- stability

STABILITY_FORMAT = (
    JSON_TAIL + '{"day_pillar": "<stem><branch>", "day_master_element": "<element>", '
    '"strength": "<strong|weak|balanced>", "favorable_elements": ["<element>", ...], '
    '"unfavorable_elements": ["<element>", ...]}  - always include this, whatever the question asked.'
)

# (variant name, template). Every variant should yield the same core facts.
STABILITY_VARIANTS = [
    ("direct_en", lambda b: f"I'm a {birth_text(b)}. What's my Day Master, is it strong or weak, "
                            f"and which elements are favorable for me?"),
    ("career_en", lambda b: f"Chart for a {birth_text(b)}. Based on the chart's core balance, "
                            f"which kinds of careers suit me?"),
    ("casual_en", lambda b: f"quick one - {birth_text(b)}. what elements should i lean into and avoid?"),
    ("direct_zh", lambda b: f"{birth_text_zh(b)}。请问我的日主是什么，身强还是身弱，喜用神是什么？"),
    ("relationship_zh", lambda b: f"{birth_text_zh(b)}。从命局的整体平衡看，我的感情运势如何？"),
]


def stability_records(charts):
    out = []
    for chart_id, birth, chart in charts:
        s = chart["strength"]
        gold = {
            "day_pillar": chart["pillars"]["day"],
            "day_master_element": s["day_master_element"],
            "strength": s["strength"],
            "favorable_elements": s["favorable_elements"],
            "unfavorable_elements": s["unfavorable_elements"],
        }
        for i, (name, template) in enumerate(STABILITY_VARIANTS):
            out.append(record(
                "stability", "core_reading", chart_id, birth, chart,
                template(birth), STABILITY_FORMAT, gold,
                group_id=f"stab-{chart_id}", variant=name,
                # Repeat only the canonical ask; other variants measure wording drift.
                repeats=STABILITY_REPEATS if i == 0 else 1,
            ))
    return out


# ---------------------------------------------------------------- interactions

INTERACTION_FORMAT = (
    JSON_TAIL + '{"interactions": [{"type": "<clash|combination|three_harmony|punishment|harm|break>", '
    '"branches": ["<branch>", ...]}]}  - list every interaction among the four natal branches '
    '(use an empty list if there are none). For a partial three-harmony list only the two branches present; '
    'for self-punishment list the branch twice.'
)


def interaction_records(charts):
    out = []
    for chart_id, birth, chart in charts:
        ixs = chart["branch_interactions"]
        gold = {
            "keys": sorted({interaction_key(ix) for ix in ixs}),
            "interactions": ixs,
        }
        p = chart["pillars"]
        out.append(record(
            "interactions", "branch_interactions", chart_id, birth, chart,
            f"For a {birth_text(birth)}, what Earthly Branch interactions (沖合刑害破, three-harmonies) "
            f"exist among the four natal branches?",
            INTERACTION_FORMAT, gold,
        ))
        out.append(record(
            "interactions", "branch_interactions", chart_id, birth, chart,
            f"A Bazi chart has pillars {pillars_text(p)}. What Earthly Branch interactions "
            f"(沖合刑害破, three-harmonies) exist among its four branches?",
            INTERACTION_FORMAT, gold,
            input_mode="pillars", pillars_given=p,
        ))
    return out


def pick_interaction_charts(stream, sizes):
    """Fills each interaction-count bucket, preferring charts that bring in an
    interaction type not yet covered so rarer types (punishment, full
    three-harmony) actually show up."""
    buckets = {k: [] for k in sizes}
    seen_types = set()
    for draw in range(20000):
        if all(len(buckets[k]) >= n for k, n in sizes.items()):
            break
        birth, chart = next(stream)
        ixs = chart["branch_interactions"]
        k = min(len(ixs), 4)
        if len(buckets[k]) >= sizes[k]:
            continue
        types = {(ix["type"], ix["note"] if ix["type"] in ("punishment", "three_harmony") else None) for ix in ixs}
        # For the first draws, hold each bucket's last two slots for charts
        # adding new coverage; after that, accept anything so buckets fill.
        if draw < 3000 and k and not (types - seen_types) and len(buckets[k]) >= sizes[k] - 2:
            continue
        seen_types |= types
        buckets[k].append((birth, chart))
    return [pair for k in sorted(buckets) for pair in buckets[k]]


# ---------------------------------------------------------------- edge

# city -> (latitude, longitude, IANA time zone). The reference converts clock
# time with this zone; generation checks the engine's own zone lookup
# (timezonefinder) agrees, so a disagreement there can't be what fails.
EDGE_CITIES = {
    "Beijing": (39.9042, 116.4074, "Asia/Shanghai"),
    "Shanghai": (31.2304, 121.4737, "Asia/Shanghai"),
    "Lhasa": (29.6520, 91.1721, "Asia/Shanghai"),        # Beijing time ~2h ahead of the sun
    "Kunming": (25.0389, 102.7183, "Asia/Shanghai"),
    "Hong Kong": (22.3193, 114.1694, "Asia/Hong_Kong"),
    "Taipei": (25.0330, 121.5654, "Asia/Taipei"),
    "Singapore": (1.3521, 103.8198, "Asia/Singapore"),   # UTC+7:30 until 1982
    "Tokyo": (35.6762, 139.6503, "Asia/Tokyo"),
    "Kolkata": (22.5726, 88.3639, "Asia/Kolkata"),
    "Kathmandu": (27.7172, 85.3240, "Asia/Kathmandu"),   # UTC+5:45
    "London": (51.5074, -0.1278, "Europe/London"),
    "New York": (40.7128, -74.0060, "America/New_York"),
    "Los Angeles": (34.0522, -118.2437, "America/Los_Angeles"),
    "St. John's": (47.5615, -52.7126, "America/St_Johns"),  # UTC-3:30
    "Sydney": (-33.8688, 151.2093, "Australia/Sydney"),
    "Adelaide": (-34.9285, 138.6007, "Australia/Adelaide"),  # UTC+9:30
    "Honolulu": (21.3069, -157.8583, "Pacific/Honolulu"),
}
CHINESE_CALENDAR_CITIES = ["Beijing", "Shanghai", "Hong Kong", "Taipei", "Singapore"]

EDGE_CATEGORIES = ("solar_term", "li_chun", "zi_hour", "time_zone", "equation_of_time", "leap_month")

ZI_CONVENTION = ("If the birth falls between 23:00 and 24:00 true solar time (late 子時), use the convention "
                 "that keeps the current day's Day Pillar and takes the next day's stem for the Hour Pillar.")
EDGE_FORMAT = (JSON_TAIL + '{"year_pillar": "<stem><branch>", "month_pillar": "<stem><branch>", '
               '"day_pillar": "<stem><branch>", "hour_pillar": "<stem><branch>"}')

# (scenario, cities, date picker) for the time_zone category: places and eras
# where reading the clock as solar time puts the birth in the wrong hour.
def _any_date(rng, start=1955, end=2020):
    return date(start, 1, 1) + timedelta(days=rng.randrange((end - start + 1) * 365))


TIME_ZONE_SCENARIOS = [
    ("lhasa_beijing_time", ["Lhasa"], lambda rng: _any_date(rng)),
    ("china_dst_1986_1991", ["Beijing", "Shanghai"],
     lambda rng: date(rng.randint(1986, 1991), rng.choice([6, 7, 8]), rng.randint(1, 28))),
    ("us_summer_dst", ["New York", "Los Angeles"], lambda rng: date(rng.randint(1960, 2020), 7, rng.randint(1, 28))),
    ("singapore_utc_0730", ["Singapore"], lambda rng: _any_date(rng, 1955, 1981)),
    ("adelaide_summer_dst", ["Adelaide"], lambda rng: date(rng.randint(1990, 2020), 1, rng.randint(1, 28))),
    ("half_hour_offsets", ["St. John's", "Kathmandu", "Kolkata"], lambda rng: _any_date(rng, 1990, 2020)),
    ("date_shift_past_midnight", ["Lhasa", "Kunming", "Los Angeles"], None),  # time picked separately
]


def _edge_ref(birth, equation_of_time=True):
    from bench import reference
    lat, lng, tz = EDGE_CITIES[birth["city"]]
    return reference.pillars(birth["year"], birth["month"], birth["day"], birth["hour"], birth["minute"],
                             tz, lng, equation_of_time)


def _birth_at_utc(utc, city, gender):
    local = utc.astimezone(ZoneInfo(EDGE_CITIES[city][2]))
    return {"year": local.year, "month": local.month, "day": local.day, "hour": local.hour,
            "minute": local.minute, "gender": gender, "city": city}


def _utc_for_solar_time(solar, city):
    """UTC instant at which local apparent solar time in `city` reads `solar`."""
    from bench.reference import apparent_solar_time
    lng = EDGE_CITIES[city][1]
    utc = (solar - timedelta(hours=lng / 15)).replace(tzinfo=timezone.utc)
    for _ in range(2):  # the equation of time barely moves within minutes
        _, eot = apparent_solar_time(utc, lng)
        utc = (solar - timedelta(hours=lng / 15, minutes=eot)).replace(tzinfo=timezone.utc)
    return utc + timedelta(seconds=30)  # land mid-minute, so truncating to the minute stays on target


def _hour_branch(h):
    return ((h + 1) // 2) % 12


def edge_candidate(category, rng):
    """One candidate birth for `category`: (birth, scenario, focus pillars, extra meta)."""
    from bench import reference
    gender = rng.choice(["Male", "Female"])
    city = rng.choice(sorted(EDGE_CITIES))

    if category in ("solar_term", "li_chun"):
        month_index = 0 if category == "li_chun" else rng.randint(1, 11)
        jie = reference.find_jie(month_index, rng.randint(1955, 2024))
        offset = rng.choice([-1, 1]) * rng.choice([20, 45, 90, 180, 360, 600])
        birth = _birth_at_utc(jie + timedelta(minutes=offset, seconds=30), city, gender)
        focus = ["year", "month"] if category == "li_chun" else ["month"]
        return birth, reference.JIE[month_index], focus, {"minutes_from_jie": offset}

    if category == "zi_hour":
        d = _any_date(rng)
        late = rng.random() < 0.5
        solar = datetime(d.year, d.month, d.day, 23 if late else 0, rng.randint(5, 54))
        birth = _birth_at_utc(_utc_for_solar_time(solar, city), city, gender)
        return birth, "late_zi" if late else "early_zi", ["day", "hour"], {}

    if category == "time_zone":
        scenario, cities, pick_date = rng.choice(TIME_ZONE_SCENARIOS)
        city = rng.choice(cities)
        if pick_date is None:  # just past local midnight, so the solar date is the previous day
            d = _any_date(rng)
            birth = {"year": d.year, "month": d.month, "day": d.day, "hour": rng.choice([0, 1]),
                     "minute": rng.randint(0, 59), "gender": gender, "city": city}
            return birth, scenario, ["day", "hour"], {}
        d = pick_date(rng)
        birth = {"year": d.year, "month": d.month, "day": d.day, "hour": rng.randint(1, 22),
                 "minute": rng.randint(0, 59), "gender": gender, "city": city}
        return birth, scenario, ["hour"], {}

    if category == "equation_of_time":
        # Feb (sun ~14 min behind the clock) and Nov (~16 min ahead) - the only
        # months where mean and apparent solar time can land in different
        # hours with a few minutes' margin on both sides.
        d = rng.choice([date(rng.randint(1955, 2020), 2, rng.randint(1, 20)),
                        date(rng.randint(1955, 2020), 11, rng.randint(1, 15))])
        lng = EDGE_CITIES[city][1]
        _, eot = reference.apparent_solar_time(datetime(d.year, d.month, d.day, 12, tzinfo=timezone.utc), lng)
        boundary = rng.choice(range(3, 22, 2))
        nudge = rng.uniform(5, abs(eot) - 4)
        solar = datetime(d.year, d.month, d.day, boundary) + timedelta(minutes=nudge if eot > 0 else -nudge)
        birth = _birth_at_utc(_utc_for_solar_time(solar, city), city, gender)
        return birth, "feb" if d.month == 2 else "nov", ["hour"], {"equation_of_time_min": round(eot, 1)}

    if category == "leap_month":
        from lunar_python import Lunar, LunarYear
        city = rng.choice(CHINESE_CALENDAR_CITIES)
        while True:
            y = rng.randint(1955, 2023)
            leap = LunarYear.fromYear(y).getLeapMonth()
            if leap:
                break
        lunar = Lunar.fromYmd(y, -leap, rng.randint(1, 29))
        solar = lunar.getSolar()
        birth = {"year": solar.getYear(), "month": solar.getMonth(), "day": solar.getDay(),
                 "hour": rng.randint(8, 20), "minute": rng.randint(0, 59), "gender": gender, "city": city}
        lunar_text = f"lunar calendar: {y}年{lunar.getMonthInChinese()}月{lunar.getDayInChinese()}"
        # The trap: reading the month pillar off the (leap) lunar month.
        return birth, f"leap_{leap}", ["month"], {"lunar_date": lunar_text, "lunar_month": leap}

    raise ValueError(category)


def accept_edge(category, birth, focus, extra):
    """Gold for a candidate, or None if it isn't a clean test of `category`:
    every boundary that decides it must be at least MIN_MARGIN_MIN away, and
    only the effect under test may change the answer."""
    from bench.reference import MIN_MARGIN_MIN
    gold = _edge_ref(birth)
    mean = _edge_ref(birth, equation_of_time=False)
    if gold is None or mean is None:  # nonexistent / repeated DST clock time
        return None
    m = gold["margins_min"]
    if m["hour"] < MIN_MARGIN_MIN or m["day"] < MIN_MARGIN_MIN:
        return None
    if m["jie"] < (15 if category in ("solar_term", "li_chun") else 24 * 60):
        return None

    if category == "equation_of_time":
        if mean["pillars"]["hour"] == gold["pillars"]["hour"] or mean["margins_min"]["hour"] < 3:
            return None
        if mean["pillars"]["day"] != gold["pillars"]["day"]:
            return None
    elif mean["pillars"] != gold["pillars"]:
        return None  # the equation of time would also decide this case - not isolated

    clock_branch = _hour_branch(birth["hour"])
    solar = datetime.strptime(gold["solar_time"], "%Y-%m-%d %H:%M")
    if category == "time_zone":
        if "day" in focus and solar.date() == date(birth["year"], birth["month"], birth["day"]):
            return None
        if BRANCH_ORDER.index(gold["pillars"]["hour"][1]) == clock_branch:
            return None  # reading the clock as solar time would still be right
    if category == "leap_month":
        lunar_branch = BRANCH_ORDER[(extra["lunar_month"] + 1) % 12]  # 正月 -> 寅
        if gold["pillars"]["month"][1] == lunar_branch:
            return None  # the lunar month happens to give the right answer
    return gold, mean


def edge_records(name, rng):
    """Edge-case records: per category, cfg["edge_per_category"] births that
    pass accept_edge, with gold from bench/reference.py."""
    from timezonefinder import TimezoneFinder
    tf = TimezoneFinder()
    for city, (lat, lng, tz) in EDGE_CITIES.items():
        engine_tz = tf.timezone_at(lng=lng, lat=lat)
        if ZoneInfo(engine_tz).key != tz and engine_tz != tz:
            raise SystemExit(f"{city}: engine resolves {engine_tz}, reference uses {tz}")

    exclude = set()
    if name != "edge-eval" and set_path("edge-eval").exists():
        exclude = {json.dumps(q["birth"], sort_keys=True) for q in map(json.loads, set_path("edge-eval").open(encoding="utf-8"))}

    out = []
    n = SETS[name]["edge_per_category"]
    for category in EDGE_CATEGORIES:
        accepted = 0
        for _ in range(5000):
            if accepted >= n:
                break
            birth, scenario, focus, extra = edge_candidate(category, rng)
            if json.dumps(birth, sort_keys=True) in exclude:
                continue
            result = accept_edge(category, birth, focus, extra)
            if result is None:
                continue
            gold, mean = result
            accepted += 1
            exclude.add(json.dumps(birth, sort_keys=True))
            who = birth_text(birth)
            lunar = f" ({extra['lunar_date']})" if "lunar_date" in extra else ""
            out.append({
                "id": None, "suite": "edge", "task": category,
                "chart_id": f"{SETS[name]['id_prefix']}e{len(out):03d}",
                "input_mode": "birth", "birth": birth, "pillars_given": None,
                "question": f"For a {who}{lunar}, what are the Four Pillars (year, month, day and hour) "
                            f"of their Bazi chart? {ZI_CONVENTION}",
                "answer_format": EDGE_FORMAT,
                "gold": {"pillars": gold["pillars"], "focus": focus,
                         "mean_solar_time_pillars": mean["pillars"],
                         "reference": {k: v for k, v in gold.items() if k != "pillars"}},
                "group_id": None, "variant": scenario, "repeats": 1,
                "meta": {"category": category, "tst_changes_chart": True, **extra},
            })
        if accepted < n:
            raise SystemExit(f"edge category {category}: only {accepted}/{n} clean cases found")
    return out


def git_sha():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        return None


def set_path(name):
    return DATA_DIR / f"{name}.jsonl"


def file_sha256(path):
    # Line endings normalized: git may check the file out as CRLF on Windows.
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def eval_pillar_keys():
    """Pillars of every eval chart, so dev never reuses one."""
    path = set_path("eval")
    if not path.exists():
        return frozenset()
    births = {json.dumps(q["birth"], sort_keys=True) for q in map(json.loads, path.open(encoding="utf-8"))}
    return frozenset(pillar_key(build_chart(json.loads(b))["pillars"]) for b in births)


def build_records(name, seed=None):
    cfg = SETS[name]
    seed = cfg["seed"] if seed is None else seed
    rng = random.Random(seed)
    pre = cfg["id_prefix"]

    if "edge_per_category" in cfg:
        records = edge_records(name, rng)
    else:
        time_engine.geolocator.geocode = _stub_geocode
        stream = sample_charts(rng, exclude=eval_pillar_keys() if name != "eval" else frozenset())

        acc = [next(stream) for _ in range(cfg["accuracy_charts"])]
        stab = [next(stream) for _ in range(cfg["stability_charts"])]
        inter = pick_interaction_charts(stream, cfg["interaction_buckets"])

        def ids(prefix, pairs):
            return [(f"{pre}{prefix}{i:03d}", b, c) for i, (b, c) in enumerate(pairs)]

        records = (
            accuracy_records(ids("a", acc), rng)
            + stability_records(ids("s", stab))
            + interaction_records(ids("i", inter))
        )
    meta = {"schema_version": SCHEMA_VERSION, "seed": seed, "engine_commit": git_sha()}
    counters = {}
    for rec in records:
        prefix = "edge" if rec["suite"] == "edge" else rec["suite"][:3]
        counters[prefix] = counters.get(prefix, 0) + 1
        rec["id"] = f"{pre}{prefix}-{counters[prefix]:04d}"
        rec["meta"].update(meta)
    return records, counters


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--set", choices=sorted(SETS), default="dev")
    parser.add_argument("--seed", type=int, help="override the set's default seed (dev only)")
    args = parser.parse_args()

    path = set_path(args.set)
    if args.set in FROZEN_SETS:
        if path.exists():
            raise SystemExit(f"{path} is frozen - {args.set} is never regenerated. "
                             f"Change the dev set instead, or start a new eval file deliberately.")
        if args.seed is not None:
            raise SystemExit(f"{args.set} always uses its fixed seed")

    records, counters = build_records(args.set, args.seed)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    if args.set in FROZEN_SETS:
        (DATA_DIR / f"{args.set}.sha256").write_text(file_sha256(path) + "\n", newline="\n")
    print(f"wrote {len(records)} records to {path} ({counters})")


if __name__ == "__main__":
    main()
