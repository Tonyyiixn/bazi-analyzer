"""Scores a runner.py run against the gold answers in data/questions.jsonl.

Per suite:

- accuracy:     exact match per task (day pillar; the stem's Ten God;
                hidden stems - every stem present with the right Ten God,
                plus a partial-credit fraction). Also sliced by
                tst_changes_chart, since those charts are only right with
                true-solar-time correction.
- stability:    per chart, how often the model gives the same core answer
                (day pillar, DM element, strength, favorable/unfavorable
                elements). Split into repeat consistency (canonical wording,
                re-asked) and wording consistency (different asks, first
                repeat), plus whether the core matches gold.
- interactions: set F1 over normalized interaction keys ("clash:子-午").
                A chart with no interactions scores 1.0 only if the model
                also lists none - so inventing interactions is penalized.

A reply whose final JSON can't be parsed counts as wrong (and is reported
as a parse failure). Calls that errored are excluded and reported - re-run
runner.py with the same --run to retry them.

Run from the repo root:  python -m bench.score --run smoke
"""
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from bench.generate import BRANCH_ORDER

QUESTIONS_PATH = Path(__file__).parent / "data" / "questions.jsonl"
RESULTS_DIR = Path(__file__).parent / "results"

STEMS = "甲乙丙丁戊己庚辛壬癸"

TEN_GOD_ALIASES = {
    "Friend": ["friend", "companion", "parallel", "比肩"],
    "Rob Wealth": ["rob wealth", "robwealth", "rob-wealth", "劫財", "劫财"],
    "Eating God": ["eating god", "eatinggod", "食神"],
    "Hurting Officer": ["hurting officer", "hurtingofficer", "傷官", "伤官"],
    "Direct Wealth": ["direct wealth", "正財", "正财"],
    "Indirect Wealth": ["indirect wealth", "偏財", "偏财"],
    "Direct Officer": ["direct officer", "正官"],
    "Seven Killings": ["seven killings", "seven killing", "seven kills", "7 killings", "indirect officer",
                       "七殺", "七杀", "偏官"],
    "Direct Resource": ["direct resource", "正印"],
    "Indirect Resource": ["indirect resource", "偏印", "梟神", "枭神"],
}
TEN_GODS = {alias: name for name, aliases in TEN_GOD_ALIASES.items() for alias in aliases}

ELEMENTS = {
    "wood": "Wood", "木": "Wood", "fire": "Fire", "火": "Fire", "earth": "Earth", "土": "Earth",
    "metal": "Metal", "金": "Metal", "water": "Water", "水": "Water",
}

INTERACTION_TYPES = {
    "clash": ["clash", "沖", "冲", "六沖", "六冲"],
    "combination": ["combination", "six combination", "six_combination", "six harmony", "合", "六合"],
    "three_harmony": ["three_harmony", "three harmony", "three harmonies", "half combination",
                      "half_combination", "san he", "三合", "半合", "半三合"],
    "punishment": ["punishment", "self punishment", "self_punishment", "self-punishment", "刑", "自刑"],
    "harm": ["harm", "六害", "害", "穿"],
    "break": ["break", "destruction", "破", "六破"],
}
INTERACTION_TYPE_NAMES = {alias: name for name, aliases in INTERACTION_TYPES.items() for alias in aliases}


# ---------------------------------------------------------------- parsing

def parse_final_json(text):
    """The last JSON object in the reply - the answer format asks for it at
    the end, but models often wrap it in a code fence or add a sign-off."""
    decoder = json.JSONDecoder()
    text = text or ""
    found = None
    i = text.find("{")
    while i != -1:
        try:
            obj, end = decoder.raw_decode(text, i)
        except json.JSONDecodeError:
            i = text.find("{", i + 1)
            continue
        if isinstance(obj, dict):
            found = obj
        # Skip past the whole object so its nested dicts aren't mistaken for the answer.
        i = text.find("{", end)
    return found


def norm_ten_god(value):
    if not isinstance(value, str):
        return None
    v = value.strip().lower().replace("(", " ").replace(")", " ")
    if v in TEN_GODS:
        return TEN_GODS[v]
    # "Seven Killings (七殺)" or "正官 Direct Officer": take any alias that appears.
    hits = {name for alias, name in TEN_GODS.items() if alias in v}
    return hits.pop() if len(hits) == 1 else None


def norm_element(value):
    if not isinstance(value, str):
        return None
    v = value.strip().lower()
    return ELEMENTS.get(v) or next((e for k, e in ELEMENTS.items() if k in v), None)


def norm_elements(values):
    if not isinstance(values, list):
        return None
    return frozenset(e for e in map(norm_element, values) if e)


def norm_pillar(value):
    if not isinstance(value, str):
        return None
    chars = [c for c in value if c in STEMS or c in BRANCH_ORDER]
    return "".join(chars) if len(chars) == 2 else None


def norm_interaction_key(ix):
    if not isinstance(ix, dict):
        return None
    raw_type = str(ix.get("type", "")).strip().lower()
    itype = INTERACTION_TYPE_NAMES.get(raw_type) or f"other({raw_type})"
    branches = ix.get("branches") or []
    if isinstance(branches, str):
        branches = list(branches)
    branches = sorted((b for b in branches if isinstance(b, str) and b in BRANCH_ORDER), key=BRANCH_ORDER.index)
    if itype == "punishment" and len(branches) == 1:
        branches *= 2  # self-punishment written with the branch once
    if not branches:
        return None
    return f"{itype}:{'-'.join(branches)}"


# ---------------------------------------------------------------- per-question grading

def grade_accuracy(q, parsed):
    gold = q["gold"]
    if q["task"] == "day_pillar":
        return {"correct": norm_pillar(parsed.get("day_pillar")) == gold["day_pillar"]}
    if q["task"] == "stem_ten_god":
        return {
            "correct": norm_ten_god(parsed.get("ten_god")) == gold["ten_god"],
            "stem_correct": parsed.get("stem") == gold["stem"],
        }
    if q["task"] == "hidden_stems":
        predicted = {}
        for h in parsed.get("hidden_stems") or []:
            if isinstance(h, dict) and h.get("stem") in STEMS:
                predicted[h["stem"]] = norm_ten_god(h.get("ten_god"))
        gold_map = {h["stem"]: h["ten_god"] for h in gold["hidden_stems"]}
        right = sum(predicted.get(stem) == god for stem, god in gold_map.items())
        return {
            "correct": predicted == gold_map,
            "stems_correct": set(predicted) == set(gold_map),
            "partial": right / len(gold_map),
        }
    raise ValueError(q["task"])


def core_answer(parsed):
    return (
        norm_pillar(parsed.get("day_pillar")),
        norm_element(parsed.get("day_master_element")),
        str(parsed.get("strength", "")).strip().lower() or None,
        norm_elements(parsed.get("favorable_elements")),
        norm_elements(parsed.get("unfavorable_elements")),
    )


CORE_FIELDS = ("day_pillar", "day_master_element", "strength", "favorable_elements", "unfavorable_elements")


def gold_core(gold):
    return (gold["day_pillar"], gold["day_master_element"], gold["strength"],
            frozenset(gold["favorable_elements"]), frozenset(gold["unfavorable_elements"]))


def prf(predicted, gold):
    if not predicted and not gold:
        return 1.0, 1.0, 1.0
    tp = len(predicted & gold)
    p = tp / len(predicted) if predicted else 0.0
    r = tp / len(gold) if gold else 0.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)


# ---------------------------------------------------------------- suite reports

def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else None


def score_accuracy(rows):
    by_task = defaultdict(list)
    for q, rec, parsed in rows:
        g = grade_accuracy(q, parsed) if parsed else {"correct": False}
        by_task[q["task"]].append((q, g))
        by_task["all"].append((q, g))
    report = {}
    for task, graded in by_task.items():
        report[task] = {
            "n": len(graded),
            "accuracy": mean(g["correct"] for _, g in graded),
            "accuracy_tst_changes_chart": mean(g["correct"] for q, g in graded if q["meta"]["tst_changes_chart"]),
            "accuracy_tst_irrelevant": mean(g["correct"] for q, g in graded if not q["meta"]["tst_changes_chart"]),
        }
        if task == "hidden_stems":
            report[task]["partial_credit"] = mean(g.get("partial", 0.0) for _, g in graded)
    return report


def score_stability(rows):
    groups = defaultdict(list)
    for q, rec, parsed in rows:
        core = core_answer(parsed) if parsed else None
        groups[q["group_id"]].append((q, rec, core))

    def agreement(cores):
        """Share of answers equal to the most common one (1.0 = all agree).
        An unparseable answer never agrees with anything."""
        if len(cores) < 2:
            return None
        counts = Counter(c for c in cores if c is not None)
        return (counts.most_common(1)[0][1] if counts else 0) / len(cores)

    repeat, wording, field_agree, gold_match = [], [], defaultdict(list), []
    for group in groups.values():
        canonical = [core for q, rec, core in group if q["variant"] == group[0][0]["variant"] and q["repeats"] > 1]
        first_repeats = [core for q, rec, core in group if rec["repeat"] == 0]
        everything = [core for _, _, core in group]
        if (a := agreement(canonical)) is not None:
            repeat.append(a)
        if (a := agreement(first_repeats)) is not None:
            wording.append(a)
        for i, name in enumerate(CORE_FIELDS):
            if (a := agreement([c[i] if c else None for c in everything])) is not None:
                field_agree[name].append(a)
        gold = gold_core(group[0][0]["gold"])
        gold_match.extend(core == gold for core in everything)

    return {
        "groups": len(groups),
        "repeat_agreement": mean(repeat),
        "wording_agreement": mean(wording),
        "field_agreement": {name: mean(v) for name, v in field_agree.items()},
        "core_matches_gold": mean(gold_match),
    }


def score_interactions(rows):
    by_mode = defaultdict(list)
    for q, rec, parsed in rows:
        gold = set(q["gold"]["keys"])
        pred_list = (parsed or {}).get("interactions")
        predicted = {k for k in map(norm_interaction_key, pred_list if isinstance(pred_list, list) else []) if k}
        by_mode[q["input_mode"]].append((gold, predicted, parsed is not None))
        by_mode["all"].append((gold, predicted, parsed is not None))

    report = {}
    for mode, graded in by_mode.items():
        scores = [prf(p, g) for g, p, _ in graded]
        tp = sum(len(g & p) for g, p, _ in graded)
        n_pred = sum(len(p) for _, p, _ in graded)
        n_gold = sum(len(g) for g, _, _ in graded)
        # Undefined (None) rather than 0 when there's nothing to divide by.
        micro_p = tp / n_pred if n_pred else None
        micro_r = tp / n_gold if n_gold else None

        per_type = {}
        for itype in INTERACTION_TYPES:
            t_gold = sum(sum(k.startswith(itype + ":") for k in g) for g, _, _ in graded)
            t_pred = sum(sum(k.startswith(itype + ":") for k in p) for _, p, _ in graded)
            t_tp = sum(sum(k.startswith(itype + ":") for k in g & p) for g, p, _ in graded)
            per_type[itype] = {"gold": t_gold, "precision": t_tp / t_pred if t_pred else None,
                               "recall": t_tp / t_gold if t_gold else None}

        empty = [p for g, p, _ in graded if not g]
        report[mode] = {
            "n": len(graded),
            "macro_f1": mean(f for _, _, f in scores),
            "micro_precision": micro_p,
            "micro_recall": micro_r,
            "micro_f1": (2 * micro_p * micro_r / (micro_p + micro_r) if micro_p + micro_r else 0.0)
                        if micro_p is not None and micro_r is not None else None,
            "exact_set_match": mean(g == p for g, p, _ in graded),
            "invented_on_empty_charts": mean(bool(p) for p in empty),
            "per_type": per_type,
        }
    return report


SUITE_SCORERS = {"accuracy": score_accuracy, "stability": score_stability, "interactions": score_interactions}


# ---------------------------------------------------------------- driver

def score_arm(questions, path):
    records = [json.loads(line) for line in path.open(encoding="utf-8")]
    # A resumed run can hold a failed attempt and its later retry - keep the latest.
    latest = {}
    for rec in records:
        latest[(rec["id"], rec["repeat"])] = rec
    errors = [r for r in latest.values() if r.get("error")]
    ok = [r for r in latest.values() if not r.get("error")]

    by_suite = defaultdict(list)
    parse_failures = Counter()
    for rec in ok:
        q = questions[rec["id"]]
        parsed = parse_final_json(rec.get("response"))
        if parsed is None:
            parse_failures[q["suite"]] += 1
        by_suite[q["suite"]].append((q, rec, parsed))

    usage = Counter()
    for rec in ok:
        usage.update(rec.get("usage") or {})
    report = {
        "calls": len(latest),
        "errors": len(errors),
        "parse_failures": dict(parse_failures),
        "stop_reasons": dict(Counter(r.get("stop_reason") for r in ok)),
        "avg_tool_calls": mean(len(r.get("tool_calls") or []) for r in ok),
        "avg_latency_s": mean(r["latency_s"] for r in ok),
        "tokens": dict(usage),
    }
    for suite, rows in by_suite.items():
        report[suite] = SUITE_SCORERS[suite](rows)
    return report


def fmt(v):
    if v is None:
        return "  -  "
    return f"{v:5.1%}" if isinstance(v, float) else str(v)


def print_summary(reports):
    arms = list(reports)
    lines = []

    def row(label, getter):
        values = []
        for arm in arms:
            try:
                values.append(fmt(getter(reports[arm])))
            except (KeyError, TypeError):
                values.append("  -  ")
        lines.append(f"  {label:<34}" + "".join(f"{v:>12}" for v in values))

    lines.append(f"  {'':<34}" + "".join(f"{a:>12}" for a in arms))
    row("calls / errors", lambda r: f"{r['calls']}/{r['errors']}")
    row("parse failures", lambda r: sum(r["parse_failures"].values()))
    row("avg tool calls", lambda r: f"{r['avg_tool_calls']:.1f}")
    row("avg latency (s)", lambda r: f"{r['avg_latency_s']:.1f}")

    lines.append("accuracy")
    for task in ("day_pillar", "stem_ten_god", "hidden_stems", "all"):
        row(f"{task}", lambda r, t=task: r["accuracy"][t]["accuracy"])
    row("hidden_stems partial credit", lambda r: r["accuracy"]["hidden_stems"]["partial_credit"])
    row("all, TST changes chart", lambda r: r["accuracy"]["all"]["accuracy_tst_changes_chart"])
    row("all, TST irrelevant", lambda r: r["accuracy"]["all"]["accuracy_tst_irrelevant"])

    lines.append("stability")
    row("repeat agreement", lambda r: r["stability"]["repeat_agreement"])
    row("wording agreement", lambda r: r["stability"]["wording_agreement"])
    for name in CORE_FIELDS:
        row(f"  {name}", lambda r, n=name: r["stability"]["field_agreement"][n])
    row("core matches gold", lambda r: r["stability"]["core_matches_gold"])

    lines.append("interactions")
    for mode in ("birth", "pillars", "all"):
        row(f"macro F1 ({mode})", lambda r, m=mode: r["interactions"][m]["macro_f1"])
    row("micro P / R (all)", lambda r: f"{r['interactions']['all']['micro_precision']:.0%}/"
                                       f"{r['interactions']['all']['micro_recall']:.0%}")
    row("invented on empty charts", lambda r: r["interactions"]["all"]["invented_on_empty_charts"])
    for itype in INTERACTION_TYPES:
        row(f"  recall {itype}", lambda r, t=itype: r["interactions"]["all"]["per_type"][t]["recall"])
    print("\n".join(lines))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", default="default")
    args = parser.parse_args()

    run_dir = RESULTS_DIR / args.run
    questions = {q["id"]: q for q in map(json.loads, QUESTIONS_PATH.open(encoding="utf-8"))}
    reports = {path.stem: score_arm(questions, path) for path in sorted(run_dir.glob("*.jsonl"))}
    if not reports:
        raise SystemExit(f"no results in {run_dir}")

    (run_dir / "scores.json").write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"run: {args.run}")
    print_summary(reports)
    print(f"\nfull report: {run_dir / 'scores.json'}")


if __name__ == "__main__":
    main()
