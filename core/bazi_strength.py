"""Day Master strength (身強/身弱) scoring and favorable/unfavorable
element derivation, using the 扶抑 (Support/Suppress) method.

This is a DELIBERATE, DOCUMENTED CHOICE, not the only valid approach.
Traditional schools disagree on 用神 (favorable-element) selection - 扶抑
(support the weak, suppress the strong) is the most common baseline taught
across schools, but 調候 (seasonal temperature balance), 通關 (resolving a
conflict between two dominant elements), and 病藥 (find the chart's "illness"
and its "cure") can select DIFFERENT favorable elements for the same chart.
This app implements 扶抑 only. See
core/knowledge/principles/day_master_strength.md for the underlying theory
in prose.

The scoring itself is a simplified heuristic (weighted support-vs-drain
count, with the Month branch weighted double for 得令/seasonal command,
traditionally the single most decisive factor) - it does not account for
combinations/clashes that alter effective rootedness, or the "distance"
between characters. Treat the result as a structured starting signal you
can inspect and reason further from (via the "factors" breakdown), not an
uncontested final verdict.
"""

from core.bazi_math import get_ten_god, BRANCH_MAIN_QI, STEM_ATTRIBUTES

SUPPORT_TEN_GODS = {'Friend', 'Rob Wealth', 'Direct Resource', 'Indirect Resource'}
DRAIN_TEN_GODS = {
    'Eating God', 'Hurting Officer',
    'Direct Wealth', 'Indirect Wealth',
    'Direct Officer', 'Seven Killings',
}

GENERATING_CYCLE = {
    'Wood': 'Fire', 'Fire': 'Earth', 'Earth': 'Metal', 'Metal': 'Water', 'Water': 'Wood',
}
CONTROLLING_CYCLE = {
    'Wood': 'Earth', 'Earth': 'Water', 'Water': 'Fire', 'Fire': 'Metal', 'Metal': 'Wood',
}
GENERATED_BY = {v: k for k, v in GENERATING_CYCLE.items()}   # element -> what generates it
CONTROLLED_BY = {v: k for k, v in CONTROLLING_CYCLE.items()}  # element -> what controls it


def analyze_day_master_strength(pillars):
    """Scores Day Master strength via 扶抑: classifies each of the chart's
    other 7 characters (3 stems + 4 branches, via each branch's dominant
    hidden stem) as supporting the Day Master (Friend/Rob Wealth, Resource)
    or draining/opposing it (Output, Wealth, Officer). The Month branch
    counts double for 得令 (seasonal command).

    Returns {"day_master", "day_master_element", "strength" ("strong"/
    "weak"/"balanced"), "support_weight", "drain_weight", "factors" (list
    of {"position","character","ten_god","category","weight"}),
    "favorable_elements", "unfavorable_elements", "method", "note"}."""
    day_master = pillars['day'][0]
    dm_element = STEM_ATTRIBUTES[day_master]['element']

    # (position label, character, weight)
    characters = [
        ("year_stem", pillars['year'][0], 1),
        ("year_branch", BRANCH_MAIN_QI[pillars['year'][1]], 1),
        ("month_stem", pillars['month'][0], 1),
        ("month_branch", BRANCH_MAIN_QI[pillars['month'][1]], 2),  # 得令 - seasonal command
        ("day_branch", BRANCH_MAIN_QI[pillars['day'][1]], 1),
        ("hour_stem", pillars['hour'][0], 1),
        ("hour_branch", BRANCH_MAIN_QI[pillars['hour'][1]], 1),
    ]

    factors = []
    support_weight = 0
    drain_weight = 0
    for position, char, weight in characters:
        ten_god = get_ten_god(day_master, char)
        if ten_god in SUPPORT_TEN_GODS:
            category = "support"
            support_weight += weight
        elif ten_god in DRAIN_TEN_GODS:
            category = "drain"
            drain_weight += weight
        else:
            category = "neutral"  # defensive only - shouldn't occur for valid characters
        factors.append({
            "position": position, "character": char, "ten_god": ten_god,
            "category": category, "weight": weight,
        })

    if support_weight > drain_weight:
        strength = "strong"
    elif support_weight < drain_weight:
        strength = "weak"
    else:
        strength = "balanced"

    note = None
    if strength == "weak":
        favorable = [dm_element, GENERATED_BY[dm_element]]
        unfavorable = [GENERATING_CYCLE[dm_element], CONTROLLING_CYCLE[dm_element], CONTROLLED_BY[dm_element]]
    elif strength == "strong":
        favorable = [GENERATING_CYCLE[dm_element], CONTROLLING_CYCLE[dm_element], CONTROLLED_BY[dm_element]]
        unfavorable = [dm_element, GENERATED_BY[dm_element]]
    else:
        favorable = []
        unfavorable = []
        note = (
            "Support and drain are evenly weighted - this simplified 扶抑 "
            "heuristic doesn't produce a clear favorable/unfavorable skew "
            "from strength alone. Other methods (調候/通關/病藥) may resolve "
            "this differently; treat this chart as genuinely balanced "
            "rather than forcing a verdict."
        )

    return {
        "day_master": day_master,
        "day_master_element": dm_element,
        "strength": strength,
        "support_weight": support_weight,
        "drain_weight": drain_weight,
        "factors": factors,
        "favorable_elements": favorable,
        "unfavorable_elements": unfavorable,
        "method": "扶抑 (Support/Suppress)",
        "note": note,
    }
