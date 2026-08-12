"""Tests for core/bazi_interactions.py - branch interaction detection.

These build synthetic pillar dicts (not full lunar_python charts) so each
interaction type can be tested in isolation with a precise, minimal example.
"""
from core.bazi_interactions import find_branch_interactions


def _pillars(year, month, day, hour):
    return {"year": year, "month": month, "day": day, "hour": hour}


def by_type(interactions, interaction_type):
    return [i for i in interactions if i["type"] == interaction_type]


def test_no_interactions_for_repeated_non_special_branch():
    # All four pillars share the same branch (子), which isn't in any
    # clash/combination/harm/break pair with itself, and isn't one of the
    # self-punishing branches - so nothing should fire.
    pillars = _pillars("甲子", "丙子", "戊子", "庚子")
    assert find_branch_interactions(pillars) == []


def test_clash_detected_with_correct_positions():
    pillars = _pillars("甲子", "丙午", "戊寅", "庚辰")  # year=子, month=午 -> clash
    clashes = by_type(find_branch_interactions(pillars), "clash")
    assert len(clashes) == 1
    assert set(clashes[0]["branches"]) == {"子", "午"}
    assert clashes[0]["positions"] == ["year", "month"]


def test_combination_with_resulting_element():
    pillars = _pillars("甲子", "乙丑", "戊寅", "庚辰")  # year=子, month=丑 -> combine to Earth
    combos = by_type(find_branch_interactions(pillars), "combination")
    assert len(combos) == 1
    assert set(combos[0]["branches"]) == {"子", "丑"}
    assert combos[0]["element"] == "Earth"


def test_wu_wei_combination_has_no_element():
    pillars = _pillars("甲午", "乙未", "戊寅", "庚辰")  # year=午, month=未 -> combine, no transformation
    combos = by_type(find_branch_interactions(pillars), "combination")
    assert len(combos) == 1
    assert combos[0]["element"] is None


def test_three_harmony_full_when_all_three_present():
    # 申子辰 -> Water, one in each of year/month/day
    pillars = _pillars("庚申", "丙子", "戊辰", "壬寅")
    harmonies = by_type(find_branch_interactions(pillars), "three_harmony")
    assert len(harmonies) == 1
    assert harmonies[0]["note"] == "full"
    assert harmonies[0]["element"] == "Water"
    assert set(harmonies[0]["branches"]) == {"申", "子", "辰"}


def test_three_harmony_partial_when_two_of_three_present():
    # Only 申 and 子 present (辰 missing) -> partial Water harmony
    pillars = _pillars("庚申", "丙子", "戊寅", "壬卯")
    harmonies = by_type(find_branch_interactions(pillars), "three_harmony")
    assert len(harmonies) == 1
    assert harmonies[0]["note"] == "partial"
    assert set(harmonies[0]["branches"]) == {"申", "子"}


def test_self_punishment_when_branch_repeats():
    pillars = _pillars("甲辰", "丙寅", "戊辰", "庚午")  # 辰 appears twice
    punishments = by_type(find_branch_interactions(pillars), "punishment")
    self_punishments = [p for p in punishments if "self-punishment" in (p["note"] or "")]
    assert len(self_punishments) == 1
    assert self_punishments[0]["branches"] == ["辰", "辰"]
    assert self_punishments[0]["positions"] == ["year", "day"]


def test_bullying_punishment_triangle():
    pillars = _pillars("甲寅", "丙巳", "戊申", "庚子")  # 寅巳申 all present
    punishments = by_type(find_branch_interactions(pillars), "punishment")
    bullying = [p for p in punishments if "bullying" in (p["note"] or "")]
    assert len(bullying) == 1
    assert set(bullying[0]["branches"]) == {"寅", "巳", "申"}


def test_rudeness_punishment_pair():
    pillars = _pillars("甲子", "丁卯", "戊申", "庚戌")  # 子卯 present
    punishments = by_type(find_branch_interactions(pillars), "punishment")
    rudeness = [p for p in punishments if "rudeness" in (p["note"] or "")]
    assert len(rudeness) == 1
    assert set(rudeness[0]["branches"]) == {"子", "卯"}


def test_harm_detected():
    pillars = _pillars("甲子", "丁未", "戊寅", "庚辰")  # 子未 -> harm
    harms = by_type(find_branch_interactions(pillars), "harm")
    assert len(harms) == 1
    assert set(harms[0]["branches"]) == {"子", "未"}


def test_break_detected():
    pillars = _pillars("甲子", "乙酉", "戊寅", "庚辰")  # 子酉 -> break
    breaks = by_type(find_branch_interactions(pillars), "break")
    assert len(breaks) == 1
    assert set(breaks[0]["branches"]) == {"子", "酉"}


def test_tables_match_the_rag_principle_doc():
    """Cross-check the code's tables against the exact pairings written in
    core/knowledge/principles/branch_clashes_and_combinations.md, so the
    computed answer and the retrieved principle text can never disagree."""
    from core.bazi_interactions import (
        SIX_CLASHES, SIX_HARMS, SIX_BREAKS,
        PUNISHMENT_BULLYING, PUNISHMENT_INGRATITUDE, PUNISHMENT_RUDENESS,
        SELF_PUNISH_BRANCHES,
    )
    assert set(map(frozenset, SIX_CLASHES)) == {
        frozenset(p) for p in [('子', '午'), ('丑', '未'), ('寅', '申'), ('卯', '酉'), ('辰', '戌'), ('巳', '亥')]
    }
    assert set(map(frozenset, SIX_HARMS)) == {
        frozenset(p) for p in [('子', '未'), ('丑', '午'), ('寅', '巳'), ('卯', '辰'), ('申', '亥'), ('酉', '戌')]
    }
    assert set(map(frozenset, SIX_BREAKS)) == {
        frozenset(p) for p in [('子', '酉'), ('午', '卯'), ('巳', '申'), ('亥', '寅'), ('辰', '丑'), ('戌', '未')]
    }
    assert set(PUNISHMENT_BULLYING) == {'寅', '巳', '申'}
    assert set(PUNISHMENT_INGRATITUDE) == {'丑', '戌', '未'}
    assert set(PUNISHMENT_RUDENESS) == {'子', '卯'}
    assert set(SELF_PUNISH_BRANCHES) == {'辰', '午', '酉', '亥'}
