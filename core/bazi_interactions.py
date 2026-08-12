"""Detects Earthly Branch interactions in a Bazi chart - clashes,
combinations, three-harmonies, punishments, harms, and breaks - as
deterministic rule application, not LLM judgment.

The tables here are kept in lockstep with
core/knowledge/principles/branch_clashes_and_combinations.md (the RAG
principle doc covering this same theory in prose) so a computed answer here
never contradicts what search_bazi_principles retrieves.
"""

PILLAR_ORDER = ['year', 'month', 'day', 'hour']

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


def _branch_positions(pillars):
    """{'子': ['year', 'hour'], ...} - which pillar(s) each branch sits in."""
    positions = {}
    for key in PILLAR_ORDER:
        pillar = pillars.get(key)
        if not pillar or len(pillar) < 2:
            continue
        branch = pillar[1]
        positions.setdefault(branch, []).append(key)
    return positions


def find_branch_interactions(pillars):
    """Scans a chart's four branches (Year/Month/Day/Hour) for every
    interaction type. Returns a list of:
    {"type", "branches", "positions", "element", "note"} dicts - "element"
    and "note" are None when not applicable to that interaction type."""
    positions = _branch_positions(pillars)
    present = set(positions.keys())
    results = []

    def add(interaction_type, branches, element=None, note=None):
        involved_positions = sorted(
            {p for b in branches for p in positions.get(b, [])},
            key=PILLAR_ORDER.index,
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
