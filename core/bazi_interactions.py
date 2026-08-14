"""Detects Earthly Branch and Heavenly Stem interactions in a Bazi chart -
clashes, combinations, three-harmonies, punishments, harms, breaks, and
stem combinations - as deterministic rule application, not LLM judgment.

The tables here are kept in lockstep with the RAG principle docs covering
this same theory in prose (branch_clashes_and_combinations.md,
stem_combinations.md) so a computed answer here never contradicts what
search_bazi_principles retrieves.
"""

from datetime import date

from core.bazi_math import STEM_ATTRIBUTES, BRANCH_MAIN_QI, get_ten_god, get_year_pillar, get_month_pillar

PILLAR_ORDER = ['year', 'month', 'day', 'hour']

GENERATING_CYCLE = {
    'Wood': 'Fire', 'Fire': 'Earth', 'Earth': 'Metal', 'Metal': 'Water', 'Water': 'Wood',
}

# stem pair -> resulting element (天干五合)
STEM_COMBINATIONS = {
    frozenset(('甲', '己')): 'Earth',
    frozenset(('乙', '庚')): 'Metal',
    frozenset(('丙', '辛')): 'Water',
    frozenset(('丁', '壬')): 'Wood',
    frozenset(('戊', '癸')): 'Fire',
}

SIX_CLASHES = [
    ('子', '午'), ('丑', '未'), ('寅', '申'),
    ('卯', '酉'), ('辰', '戌'), ('巳', '亥'),
]

# branch pair -> resulting element, or None for Wu-Wei's near-neutral pairing
SIX_COMBINATIONS = {
    frozenset(('子', '丑')): 'Earth',
    frozenset(('寅', '亥')): 'Wood',
    frozenset(('卯', '戌')): 'Fire',
    frozenset(('辰', '酉')): 'Metal',
    frozenset(('巳', '申')): 'Water',
    frozenset(('午', '未')): None,
}

THREE_HARMONIES = {
    'Water': ['申', '子', '辰'],
    'Wood': ['亥', '卯', '未'],
    'Fire': ['寅', '午', '戌'],
    'Metal': ['巳', '酉', '丑'],
}

SIX_HARMS = [
    ('子', '未'), ('丑', '午'), ('寅', '巳'),
    ('卯', '辰'), ('申', '亥'), ('酉', '戌'),
]

SIX_BREAKS = [
    ('子', '酉'), ('午', '卯'), ('巳', '申'),
    ('亥', '寅'), ('辰', '丑'), ('戌', '未'),
]

PUNISHMENT_BULLYING = ('寅', '巳', '申')       # 恃勢之刑 - bullying/power
PUNISHMENT_INGRATITUDE = ('丑', '戌', '未')    # 無恩之刑 - ingratitude
PUNISHMENT_RUDENESS = ('子', '卯')             # 無禮之刑 - rudeness, mutual pair
SELF_PUNISH_BRANCHES = ('辰', '午', '酉', '亥')  # 自刑 - punishes itself when repeated


def _branch_positions(pillars, pillar_order=PILLAR_ORDER):
    """{'子': ['year', 'hour'], ...} - which pillar(s) each branch sits in."""
    positions = {}
    for key in pillar_order:
        pillar = pillars.get(key)
        if not pillar or len(pillar) < 2:
            continue
        branch = pillar[1]
        positions.setdefault(branch, []).append(key)
    return positions


def find_branch_interactions(pillars, pillar_order=PILLAR_ORDER):
    """Scans a chart's branches (by default Year/Month/Day/Hour, but
    `pillar_order` can name a different/extended set of keys - e.g. to
    include an injected Liu Nian pillar) for every interaction type.
    Returns a list of {"type", "branches", "positions", "element", "note"}
    dicts - "element" and "note" are None when not applicable."""
    positions = _branch_positions(pillars, pillar_order)
    present = set(positions.keys())
    results = []

    def add(interaction_type, branches, element=None, note=None):
        involved_positions = sorted(
            {p for b in branches for p in positions.get(b, [])},
            key=pillar_order.index,
        )
        results.append({
            "type": interaction_type,
            "branches": list(branches),
            "positions": involved_positions,
            "element": element,
            "note": note,
        })

    for a, b in SIX_CLASHES:
        if a in present and b in present:
            add("clash", (a, b))

    for pair, element in SIX_COMBINATIONS.items():
        a, b = tuple(pair)
        if a in present and b in present:
            add("combination", (a, b), element=element)

    for element, trio in THREE_HARMONIES.items():
        present_in_trio = [b for b in trio if b in present]
        if len(present_in_trio) == 3:
            add("three_harmony", trio, element=element, note="full")
        elif len(present_in_trio) == 2:
            add("three_harmony", present_in_trio, element=element, note="partial")

    bullying_present = [b for b in PUNISHMENT_BULLYING if b in present]
    if len(bullying_present) >= 2:
        add("punishment", bullying_present, note="bullying/power (恃勢之刑)")

    ingratitude_present = [b for b in PUNISHMENT_INGRATITUDE if b in present]
    if len(ingratitude_present) >= 2:
        add("punishment", ingratitude_present, note="ingratitude (無恩之刑)")

    if all(b in present for b in PUNISHMENT_RUDENESS):
        add("punishment", PUNISHMENT_RUDENESS, note="rudeness (無禮之刑)")

    for b in SELF_PUNISH_BRANCHES:
        if len(positions.get(b, [])) >= 2:
            add("punishment", (b, b), note="self-punishment (自刑)")

    for a, b in SIX_HARMS:
        if a in present and b in present:
            add("harm", (a, b))

    for a, b in SIX_BREAKS:
        if a in present and b in present:
            add("break", (a, b))

    return results


def find_stem_combinations(pillars):
    """Detects Heavenly Stem combinations (天干五合) between ADJACENT
    pillars' stems (Year-Month, Month-Day, Day-Hour) - per the RAG doc's
    practical note, a stem combination between non-adjacent pillars is a
    much weaker, often-ignored effect, so it's deliberately not flagged here.

    Each result includes "involves_day_master" (traditionally the most
    significant case - see stem_combinations.md) and a
    "season_supports_transformation" heuristic: whether the Month branch's
    own element matches or is generated toward the combination's resulting
    element. This is only ONE of the traditional conditions for true
    transformation (合化) vs. a structural-only combination (合而不化) - it
    does not check whether the resulting element is opposed elsewhere in
    the chart, so treat it as a signal to weigh, not a verdict."""
    stems = {}
    for key in PILLAR_ORDER:
        pillar = pillars.get(key)
        if pillar and len(pillar) >= 1:
            stems[key] = pillar[0]

    month_branch = pillars.get('month', '')
    month_element = None
    if month_branch and len(month_branch) >= 2:
        month_element = STEM_ATTRIBUTES.get(month_branch[1], {}).get('element')

    results = []
    for a, b in zip(PILLAR_ORDER, PILLAR_ORDER[1:]):
        if a not in stems or b not in stems:
            continue
        pair_key = frozenset((stems[a], stems[b]))
        if pair_key not in STEM_COMBINATIONS:
            continue
        element = STEM_COMBINATIONS[pair_key]
        season_supports = month_element is not None and (
            month_element == element or GENERATING_CYCLE.get(month_element) == element
        )
        results.append({
            "type": "stem_combination",
            "stems": [stems[a], stems[b]],
            "positions": [a, b],
            "element": element,
            "involves_day_master": "day" in (a, b),
            "season_supports_transformation": season_supports,
        })

    return results


LIU_NIAN_PILLAR_ORDER = PILLAR_ORDER + ['liu_nian']


def analyze_liu_nian(pillars, year):
    """Analyzes how a given year's Liu Nian (流年, annual pillar) interacts
    with a natal chart: its Ten God relationship to the Day Master, every
    branch interaction it forms against the natal branches (reusing the
    same detection tables as find_branch_interactions - not a separate,
    hand-duplicated ruleset), and whether its stem forms a Heavenly Stem
    combination with the Day Master specifically. The Day Master is the
    only stem checked for a Liu Nian combination because that's the case
    stem_combinations.md calls out as traditionally significant regardless
    of adjacency - general Liu-Nian-vs-any-natal-stem combinations are not
    checked, matching that doc's "especially the Day Master" guidance.

    Returns {"year", "pillar", "ten_gods", "branch_interactions",
    "stem_combination_with_day_master"} - the latter is None if the Liu
    Nian stem doesn't pair with the Day Master at all."""
    liu_nian_pillar = get_year_pillar(year)
    stem, branch = liu_nian_pillar[0], liu_nian_pillar[1]
    day_master = pillars['day'][0]

    ten_gods = {
        'stem': get_ten_god(day_master, stem),
        'branch': get_ten_god(day_master, BRANCH_MAIN_QI[branch]),
    }

    extended_pillars = {**pillars, 'liu_nian': liu_nian_pillar}
    all_interactions = find_branch_interactions(extended_pillars, pillar_order=LIU_NIAN_PILLAR_ORDER)
    branch_interactions = [i for i in all_interactions if 'liu_nian' in i['positions']]

    stem_combination_with_day_master = None
    pair_key = frozenset((stem, day_master))
    if pair_key in STEM_COMBINATIONS:
        element = STEM_COMBINATIONS[pair_key]
        month_branch = pillars.get('month', '')
        month_element = (
            STEM_ATTRIBUTES.get(month_branch[1], {}).get('element')
            if len(month_branch) >= 2 else None
        )
        season_supports = month_element is not None and (
            month_element == element or GENERATING_CYCLE.get(month_element) == element
        )
        stem_combination_with_day_master = {
            "stems": [stem, day_master],
            "element": element,
            "season_supports_transformation": season_supports,
        }

    return {
        "year": year,
        "pillar": liu_nian_pillar,
        "ten_gods": ten_gods,
        "branch_interactions": branch_interactions,
        "stem_combination_with_day_master": stem_combination_with_day_master,
    }


LIU_YUE_PILLAR_ORDER = LIU_NIAN_PILLAR_ORDER + ['liu_yue']


def analyze_liu_yue(pillars, year, month, day):
    """Analyzes how a given month's Liu Yue (流月, monthly pillar) interacts
    with a natal chart - same shape as analyze_liu_nian, but for the month
    layer. Also computes that month's containing Liu Nian (annual pillar)
    and includes it in the interaction scan, since a month is traditionally
    read together with its year, not in isolation - a Liu Yue clash against
    the Liu Nian pillar itself is as meaningful as one against a natal
    branch. `day` matters (not just year/month): Bazi months are bounded by
    solar terms, not the 1st of the Gregorian month - see get_month_pillar.

    Returns {"year", "month", "liu_nian_pillar", "pillar", "ten_gods",
    "branch_interactions", "stem_combination_with_day_master"} -
    "branch_interactions" includes interactions against BOTH the natal
    branches and the Liu Nian branch."""
    liu_nian_pillar = get_year_pillar(year)
    liu_yue_pillar = get_month_pillar(year, month, day)
    stem, branch = liu_yue_pillar[0], liu_yue_pillar[1]
    day_master = pillars['day'][0]

    ten_gods = {
        'stem': get_ten_god(day_master, stem),
        'branch': get_ten_god(day_master, BRANCH_MAIN_QI[branch]),
    }

    extended_pillars = {**pillars, 'liu_nian': liu_nian_pillar, 'liu_yue': liu_yue_pillar}
    all_interactions = find_branch_interactions(extended_pillars, pillar_order=LIU_YUE_PILLAR_ORDER)
    branch_interactions = [i for i in all_interactions if 'liu_yue' in i['positions']]

    stem_combination_with_day_master = None
    pair_key = frozenset((stem, day_master))
    if pair_key in STEM_COMBINATIONS:
        element = STEM_COMBINATIONS[pair_key]
        month_branch = pillars.get('month', '')
        month_element = (
            STEM_ATTRIBUTES.get(month_branch[1], {}).get('element')
            if len(month_branch) >= 2 else None
        )
        season_supports = month_element is not None and (
            month_element == element or GENERATING_CYCLE.get(month_element) == element
        )
        stem_combination_with_day_master = {
            "stems": [stem, day_master],
            "element": element,
            "season_supports_transformation": season_supports,
        }

    return {
        "year": year,
        "month": month,
        "liu_nian_pillar": liu_nian_pillar,
        "pillar": liu_yue_pillar,
        "ten_gods": ten_gods,
        "branch_interactions": branch_interactions,
        "stem_combination_with_day_master": stem_combination_with_day_master,
    }


def get_current_period(pillars):
    """Convenience wrapper: analyzes TODAY's Liu Nian and Liu Yue together
    against a natal chart, using the server's current date - so callers
    (the agent, the REST layer) never have to pass or guess today's
    year/month/day themselves. Always computed fresh at call time, never
    cached, so it can't go stale across a long-running process or a chart
    viewed long after it was saved.

    Returns {"liu_nian": <analyze_liu_nian result>, "liu_yue": <analyze_liu_yue result>}."""
    today = date.today()
    return {
        "liu_nian": analyze_liu_nian(pillars, today.year),
        "liu_yue": analyze_liu_yue(pillars, today.year, today.month, today.day),
    }
