"""Scores a runner.py run against the gold answers in data/<set>.jsonl.

Per suite:

- accuracy:     exact match per task (day pillar; the stem's Ten God;
                hidden stems - every stem present with the right Ten God,
                plus a partial-credit fraction). Also sliced by
                tst_changes_chart, since those charts are only right with
                true-solar-time correction.
- stability:    the core answer (day pillar, DM element, strength,
                favorable/unfavorable elements), every row scored two ways
                and always shown together: agreement (does the model give the
                same answer each time - same ask repeated, different
                wordings) and gold match (is that answer right). The core is
                also split into chart facts (objectively checkable) and the
                method verdict (agreement with this engine's 扶抑 method).
- interactions: set F1 over normalized interaction keys ("clash:子-午").
                A chart with no interactions scores 1.0 only if the model
                also lists none - so inventing interactions is penalized.

A reply whose final JSON can't be parsed counts as wrong (and is reported
as a parse failure). Calls that errored are excluded and reported - re-run
runner.py with the same --run to retry them.

Run from the repo root:  python -m bench.score --run try1 [--set eval] [--failures]
"""
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from bench.generate import BRANCH_ORDER

DATA_DIR = Path(__file__).parent / "data"
RESULTS_DIR = Path(__file__).parent / "results"

STEMS = "甲乙丙丁戊己庚辛壬癸"

# $ per million tokens: (input, output, cache read, 5-minute cache write).
# First-party list prices as of 2026-10 - an estimate for budgeting, not a bill.
PRICES = {
    "claude-opus-5-5": (4.00, 20.00, 0.20, 5.00),
    "claude-sonnet-5-5": (2.00, 10.00, 0.20, 2.50),
    "claude-haiku-4-5": (1.00, 5.00, 0.10, 1.25),
    # Prompts up to 100K tokens; cache rates assumed at the usual 0.1x / 1.25x.
    "claude-haiku-5-5": (0.10, 0.50, 0.01, 0.125),
}

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

    # Each row is scored both ways - agreement (self-consistency, per chart)
    # and gold match (per answer) - and the two are always reported together:
    # a model can be consistently wrong, or right but erratic.
    # Chart facts are objectively checkable; the method verdict only measures
    # agreement with this engine's 扶抑 weighting and "balanced" threshold, so
    # it's also reported for answers whose chart facts were right, to separate
    # method disagreement from chart errors.
    project = {
        "core": lambda c: c,
        "chart_facts": lambda c: c[:2],
        "method_verdict": lambda c: c[2:],
    }
    row_specs = {
        # row name: (which answers in the chart's group, which part of the core)
        "core_repeated_ask": ("canonical", "core"),
        "core_different_wordings": ("first_repeats", "core"),
        "core_all_answers": ("everything", "core"),
        "chart_facts": ("everything", "chart_facts"),
        "method_verdict": ("everything", "method_verdict"),
        "method_verdict_given_chart_right": ("chart_right", "method_verdict"),
    }
    agree, match = defaultdict(list), defaultdict(list)
    field_agree, field_match = defaultdict(list), defaultdict(list)
    for group in groups.values():
        gold = gold_core(group[0][0]["gold"])
        everything = [core for _, _, core in group]
        subsets = {
            "canonical": [core for q, rec, core in group
                          if q["variant"] == group[0][0]["variant"] and q["repeats"] > 1],
            "first_repeats": [core for q, rec, core in group if rec["repeat"] == 0],
            "everything": everything,
            "chart_right": [c for c in everything if c and c[:2] == gold[:2]],
        }
        for row, (subset, part) in row_specs.items():
            cores = subsets[subset]
            projected = [project[part](c) if c else None for c in cores]
            if (a := agreement(projected)) is not None:
                agree[row].append(a)
            match[row].extend(p == project[part](gold) for p in projected)
        for i, name in enumerate(CORE_FIELDS):
            values = [c[i] if c else None for c in everything]
            if (a := agreement(values)) is not None:
                field_agree[name].append(a)
            field_match[name].extend(v == gold[i] for v in values)

    return {
        "groups": len(groups),
        "rows": {row: {"agreement": mean(agree[row]), "gold_match": mean(match[row]),
                       "answers": len(match[row])} for row in row_specs},
        "fields": {name: {"agreement": mean(field_agree[name]), "gold_match": mean(field_match[name])}
                   for name in CORE_FIELDS},
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


# ---------------------------------------------------------------- failed cases

def failure(q, parsed):
    """Why this reply is wrong, as {field: (gold, predicted)} - or None if
    it's right. Predictions are shown normalized, i.e. as the scorer saw them."""
    if parsed is None:
        return {"reply": ("final JSON object", "none found")}
    if q["suite"] == "accuracy":
        if grade_accuracy(q, parsed)["correct"]:
            return None
        gold = q["gold"]
        if q["task"] == "day_pillar":
            return {"day_pillar": (gold["day_pillar"], norm_pillar(parsed.get("day_pillar")) or parsed.get("day_pillar"))}
        if q["task"] == "stem_ten_god":
            return {"ten_god": (f"{gold['stem']} {gold['ten_god']}",
                                f"{parsed.get('stem')} {norm_ten_god(parsed.get('ten_god')) or parsed.get('ten_god')}")}
        predicted = [f"{h.get('stem')} {norm_ten_god(h.get('ten_god')) or h.get('ten_god')}"
                     for h in parsed.get("hidden_stems") or [] if isinstance(h, dict)]
        return {"hidden_stems": ([f"{h['stem']} {h['ten_god']}" for h in gold["hidden_stems"]], predicted)}
    if q["suite"] == "stability":
        core, gold = core_answer(parsed), gold_core(q["gold"])
        show = lambda v: sorted(v) if isinstance(v, frozenset) else v
        diffs = {name: (show(g), show(c)) for name, g, c in zip(CORE_FIELDS, gold, core) if g != c}
        return diffs or None
    gold = set(q["gold"]["keys"])
    pred_list = parsed.get("interactions")
    predicted = {k for k in map(norm_interaction_key, pred_list if isinstance(pred_list, list) else []) if k}
    if predicted == gold:
        return None
    return {"missing": (sorted(gold - predicted), None), "invented": (None, sorted(predicted - gold))}


def collect_failures(questions, path, suites=None):
    out = []
    for rec in latest_records(path).values():
        if rec.get("error"):
            continue
        q = questions[rec["id"]]
        if suites and q["suite"] not in suites:
            continue
        diffs = failure(q, parse_final_json(rec.get("response")))
        if diffs:
            out.append({"id": rec["id"], "arm": rec["arm"], "repeat": rec["repeat"], "suite": q["suite"],
                        "task": q["task"], "variant": q["variant"], "input_mode": q["input_mode"],
                        "tst_changes_chart": q["meta"]["tst_changes_chart"],
                        "diffs": diffs, "tool_calls": [t["name"] for t in rec.get("tool_calls") or []],
                        "question": q["question"], "response": rec.get("response")})
    return out


def print_failures(failures, limit):
    print(f"\nfailed cases: {len(failures)}" + (f" (showing {limit})" if len(failures) > limit else ""))
    for f in failures[:limit]:
        tags = [f["task"], f["variant"] or f["input_mode"]]
        if f["tst_changes_chart"]:
            tags.append("TST-sensitive")
        tools = ",".join(f["tool_calls"]) or "no tools"
        print(f"[{f['arm']}] {f['id']} r{f['repeat']} ({', '.join(tags)}; {tools})")
        for field, (gold, pred) in f["diffs"].items():
            if field == "missing":
                if gold:
                    print(f"    missing   {gold}")
            elif field == "invented":
                if pred:
                    print(f"    invented  {pred}")
            else:
                print(f"    {field:<20} gold {gold}  got {pred}")
        # The reasoning just before the answer JSON says more than the JSON itself.
        prose = [line for line in (f["response"] or "").strip().splitlines()
                 if line.strip() and not line.lstrip().startswith(("{", "```"))]
        print(f"    reply ends: {' / '.join(prose[-2:])[-200:]}")


# ---------------------------------------------------------------- driver

def latest_records(path):
    # A resumed run can hold a failed attempt and its later retry - keep the latest.
    latest = {}
    for line in path.open(encoding="utf-8"):
        rec = json.loads(line)
        latest[(rec["id"], rec["repeat"])] = rec
    return latest


def score_arm(questions, path):
    latest = latest_records(path)
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
    cost = 0.0
    # Errored calls can still have billed tokens, but they aren't recorded - so count ok calls only.
    for rec in ok:
        u = rec.get("usage") or {}
        usage.update(u)
        price = PRICES.get(rec.get("model"))
        if price is None:
            cost = None
        elif cost is not None:
            cost += (u.get("input_tokens", 0) * price[0] + u.get("output_tokens", 0) * price[1]
                     + u.get("cache_read_input_tokens", 0) * price[2]
                     + u.get("cache_creation_input_tokens", 0) * price[3]) / 1e6
    total_input = sum(usage[k] for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
    report = {
        "calls": len(latest),
        "errors": len(errors),
        "parse_failures": dict(parse_failures),
        "stop_reasons": dict(Counter(r.get("stop_reason") for r in ok)),
        "avg_tool_calls": mean(len(r.get("tool_calls") or []) for r in ok),
        "avg_latency_s": mean(r["latency_s"] for r in ok),
        "tokens": dict(usage),
        "cache_read_share": usage["cache_read_input_tokens"] / total_input if total_input else None,
        "est_cost_usd": round(cost, 4) if cost is not None else None,
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
    row("input tokens / call", lambda r: round(sum(r["tokens"].get(k, 0) for k in (
        "input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")) / (r["calls"] - r["errors"])))
    row("output tokens / call", lambda r: round(r["tokens"].get("output_tokens", 0) / (r["calls"] - r["errors"])))
    row("input read from cache", lambda r: r["cache_read_share"])
    row("est. cost ($)", lambda r: f"{r['est_cost_usd']:.3f}")

    lines.append("accuracy")
    for task in ("day_pillar", "stem_ten_god", "hidden_stems", "all"):
        row(f"{task}", lambda r, t=task: r["accuracy"][t]["accuracy"])
    row("hidden_stems partial credit", lambda r: r["accuracy"]["hidden_stems"]["partial_credit"])
    row("all, TST changes chart", lambda r: r["accuracy"]["all"]["accuracy_tst_changes_chart"])
    row("all, TST irrelevant", lambda r: r["accuracy"]["all"]["accuracy_tst_irrelevant"])

    # Stability gets its own two-sided table: consistency and correctness side
    # by side per row, so neither is read without the other.
    def get(r, *keys):
        try:
            for k in keys:
                r = r[k]
            return r
        except (KeyError, TypeError):
            return None

    span = 12 * len(arms)
    lines.append(f"{'stability':<36}{'agrees with itself':>{span}}{'matches gold':>{span}}")
    lines.append(f"  {'':<34}" + "".join(f"{a:>12}" for a in arms) * 2)
    labels = {
        "core_repeated_ask": "whole core, same ask repeated",
        "core_different_wordings": "whole core, different wordings",
        "core_all_answers": "whole core, all answers",
        "chart_facts": "chart facts (pillar, DM element)",
        "method_verdict": "method verdict (strength, elements)",
        "method_verdict_given_chart_right": "  ...where chart facts were right",
    }
    for key, label in labels.items():
        values = [get(reports[a], "stability", "rows", key, "agreement") for a in arms]
        values += [get(reports[a], "stability", "rows", key, "gold_match") for a in arms]
        lines.append(f"  {label:<34}" + "".join(f"{fmt(v):>12}" for v in values))

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
    parser.add_argument("--set", choices=["dev", "eval"], default="dev")
    parser.add_argument("--run", default="default")
    parser.add_argument("--failures", action="store_true", help="list failed cases (all saved to failures.jsonl)")
    parser.add_argument("--suite", nargs="+", choices=list(SUITE_SCORERS), help="limit --failures to these suites")
    parser.add_argument("--arm", nargs="+", help="limit --failures to these arms")
    parser.add_argument("--show", type=int, default=30, help="max failed cases to print")
    args = parser.parse_args()

    run_dir = RESULTS_DIR / args.set / args.run
    questions = {q["id"]: q for q in map(json.loads, (DATA_DIR / f"{args.set}.jsonl").open(encoding="utf-8"))}
    arm_files = [p for p in sorted(run_dir.glob("*.jsonl")) if p.stem != "failures"]
    reports = {path.stem: score_arm(questions, path) for path in arm_files}
    if not reports:
        raise SystemExit(f"no results in {run_dir}")

    (run_dir / "scores.json").write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"set: {args.set}  run: {args.run}")
    print_summary(reports)
    print(f"\nfull report: {run_dir / 'scores.json'}")

    if args.failures:
        failures = [f for p in arm_files if not args.arm or p.stem in args.arm
                    for f in collect_failures(questions, p, args.suite)]
        with (run_dir / "failures.jsonl").open("w", encoding="utf-8") as out:
            for f in failures:
                out.write(json.dumps(f, ensure_ascii=False) + "\n")
        print_failures(failures, args.show)
        print(f"\nall failed cases, with full replies: {run_dir / 'failures.jsonl'}")


if __name__ == "__main__":
    main()
