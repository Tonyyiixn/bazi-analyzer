"""Tests for core/bazi_interactions.py - branch and stem interaction
detection.

These build synthetic pillar dicts (not full lunar_python charts) so each
interaction type can be tested in isolation with a precise, minimal example.
"""
from datetime import date

from core.bazi_interactions import (
    find_branch_interactions, find_stem_combinations, analyze_liu_nian, analyze_liu_yue, get_current_period,
)


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


# ---------------------------------------------------------------------------
# Stem combinations (天干五合)
# ---------------------------------------------------------------------------

def test_adjacent_stem_combination_detected_with_season_support():
    # Year=甲子, Month=己丑: 甲+己 adjacent -> Earth. Month branch 丑 is Earth
    # itself, so season_supports_transformation should be True.
    pillars = _pillars("甲子", "己丑", "戊寅", "庚辰")
    combos = find_stem_combinations(pillars)
    assert len(combos) == 1
    assert set(combos[0]["stems"]) == {"甲", "己"}
    assert combos[0]["positions"] == ["year", "month"]
    assert combos[0]["element"] == "Earth"
    assert combos[0]["involves_day_master"] is False
    assert combos[0]["season_supports_transformation"] is True


def test_day_master_combination_flagged_with_low_season_support():
    # Day=丙申, Hour=辛巳: 丙+辛 adjacent -> Water. Month branch 辰 is Earth,
    # which neither matches nor generates toward Water, so season support
    # should be False. Day is involved, so involves_day_master is True.
    pillars = _pillars("甲子", "戊辰", "丙申", "辛巳")
    combos = find_stem_combinations(pillars)
    assert len(combos) == 1
    assert set(combos[0]["stems"]) == {"丙", "辛"}
    assert combos[0]["positions"] == ["day", "hour"]
    assert combos[0]["element"] == "Water"
    assert combos[0]["involves_day_master"] is True
    assert combos[0]["season_supports_transformation"] is False


def test_non_adjacent_stem_pair_is_not_flagged():
    # Year=甲 and Day=己 would combine to Earth, but they are NOT adjacent
    # (Month sits between them) - the practical convention is to ignore this.
    pillars = _pillars("甲子", "丙寅", "己巳", "壬申")
    assert find_stem_combinations(pillars) == []


def test_no_combination_when_no_pair_matches():
    pillars = _pillars("甲子", "丙寅", "戊辰", "庚午")
    assert find_stem_combinations(pillars) == []


def test_stem_combination_tables_match_the_rag_principle_doc():
    from core.bazi_interactions import STEM_COMBINATIONS
    expected = {
        frozenset(('甲', '己')): 'Earth',
        frozenset(('乙', '庚')): 'Metal',
        frozenset(('丙', '辛')): 'Water',
        frozenset(('丁', '壬')): 'Wood',
        frozenset(('戊', '癸')): 'Fire',
    }
    assert STEM_COMBINATIONS == expected


# ---------------------------------------------------------------------------
# Liu Nian (流年, annual pillar) analysis
#
# 1984 is a verified Jia-Zi (甲子) year (see test_bazi_math.py). Natal chart
# below is hand-picked so the expected result can be fully worked out by hand
# from the same tables tested above, not just re-derived by the code itself:
#
#   Natal: Year=戊午, Month=辛未, Day=己巳, Hour=甲寅  (Day Master = 己)
#   Liu Nian 1984 = 甲子 (stem 甲, branch 子)
#
#   - Ten God stem: 己(Yin Earth) vs 甲(Yang Wood) -> Wood controls Earth,
#     diff polarity -> Direct Officer
#   - Ten God branch: 子's main qi is 癸(Yin Water); 己(Yin) vs 癸(Yin) ->
#     Earth controls Water, same polarity -> Indirect Wealth
#   - Stem combination: 甲+己 is a valid pair -> Earth. Month branch 未 is
#     Earth itself, so season_supports_transformation = True
#   - Branch interactions vs natal: 子 clashes 午(year); 子 harms 未(month).
#     子 vs 巳(day) and 子 vs 寅(hour) match nothing. (寅 harms 巳, but
#     that's a purely-natal pair with no liu_nian involvement, so it must
#     NOT appear in the filtered result.)
# ---------------------------------------------------------------------------

def test_analyze_liu_nian_full_worked_example():
    pillars = _pillars("戊午", "辛未", "己巳", "甲寅")
    result = analyze_liu_nian(pillars, 1984)

    assert result["year"] == 1984
    assert result["pillar"] == "甲子"
    assert result["ten_gods"] == {"stem": "Direct Officer", "branch": "Indirect Wealth"}

    combo = result["stem_combination_with_day_master"]
    assert combo is not None
    assert set(combo["stems"]) == {"甲", "己"}
    assert combo["element"] == "Earth"
    assert combo["season_supports_transformation"] is True

    interactions = result["branch_interactions"]
    assert len(interactions) == 2

    clash = next(i for i in interactions if i["type"] == "clash")
    assert set(clash["branches"]) == {"子", "午"}
    assert clash["positions"] == ["year", "liu_nian"]

    harm = next(i for i in interactions if i["type"] == "harm")
    assert set(harm["branches"]) == {"子", "未"}
    assert harm["positions"] == ["month", "liu_nian"]

    # No purely-natal interaction (e.g. 寅-巳 harm) should leak into the
    # Liu-Nian-filtered result.
    assert all("liu_nian" in i["positions"] for i in interactions)


def test_analyze_liu_nian_no_day_master_combination_when_stems_dont_pair():
    # Day Master 甲 vs Liu Nian stem 甲 (also 1984) - same stem, not a
    # valid combination pair, so this must be None, not accidentally matched.
    pillars = _pillars("丙寅", "戊辰", "甲午", "庚午")
    result = analyze_liu_nian(pillars, 1984)
    assert result["stem_combination_with_day_master"] is None


# ---------------------------------------------------------------------------
# Liu Yue (流月, monthly pillar) analysis
#
# Same natal chart as the Liu Nian worked example above (Year=戊午, Month=辛未,
# Day=己巳, Hour=甲寅, Day Master=己). 2026-08-14 -> Liu Nian 丙午 (verified in
# test_bazi_math.py's Liu Nian tests), Liu Yue 丙申 (verified in
# test_bazi_math.py's Five Tigers rule tests). Everything below is hand-worked
# from those two already-verified pillars plus the same interaction tables
# tested in isolation above - not just a re-run of the code under test.
#
#   - Ten God stem: 己(Yin Earth) vs 丙(Yang Fire) -> Fire generates Earth,
#     diff polarity -> Direct Resource
#   - Ten God branch: 申's main qi is 庚(Yang Metal); 己(Yin) vs 庚(Yang) ->
#     Earth generates Metal, diff polarity -> Hurting Officer
#   - Stem combination: 丙(Liu Yue) + 己(Day Master) is NOT one of the 5
#     valid pairs -> None
#   - Present branches (year/month/day/hour/liu_nian/liu_yue):
#     午/未/巳/寅/午/申 (午 appears twice - year AND liu_nian)
#   - Interactions touching liu_yue(申) specifically:
#     * clash: 寅(hour) vs 申(liu_yue)
#     * combination: 巳(day) vs 申(liu_yue) -> Water
#     * punishment (bullying 恃勢之刑): 寅(hour)+巳(day)+申(liu_yue) all present
#     * break: 巳(day) vs 申(liu_yue)
#   - Interactions that exist in the full 6-branch set but do NOT touch
#     liu_yue, and must therefore be filtered OUT: the 午+未 combination,
#     the partial 寅+午 Fire three-harmony, the 午+午 self-punishment
#     (year vs liu_nian), and the 寅+巳 harm (hour vs day) - none involve 申.
# ---------------------------------------------------------------------------

def test_analyze_liu_yue_full_worked_example():
    pillars = _pillars("戊午", "辛未", "己巳", "甲寅")
    result = analyze_liu_yue(pillars, 2026, 8, 14)

    assert result["year"] == 2026
    assert result["month"] == 8
    assert result["liu_nian_pillar"] == "丙午"
    assert result["pillar"] == "丙申"
    assert result["ten_gods"] == {"stem": "Direct Resource", "branch": "Hurting Officer"}
    assert result["stem_combination_with_day_master"] is None

    interactions = result["branch_interactions"]
    assert all("liu_yue" in i["positions"] for i in interactions)

    by_type = {i["type"]: i for i in interactions}
    assert set(by_type) == {"clash", "combination", "punishment", "break"}

    assert set(by_type["clash"]["branches"]) == {"寅", "申"}
    assert by_type["clash"]["positions"] == ["hour", "liu_yue"]

    assert set(by_type["combination"]["branches"]) == {"巳", "申"}
    assert by_type["combination"]["element"] == "Water"
    assert by_type["combination"]["positions"] == ["day", "liu_yue"]

    assert set(by_type["punishment"]["branches"]) == {"寅", "巳", "申"}
    assert by_type["punishment"]["note"] == "bullying/power (恃勢之刑)"
    assert by_type["punishment"]["positions"] == ["day", "hour", "liu_yue"]

    assert set(by_type["break"]["branches"]) == {"巳", "申"}
    assert by_type["break"]["positions"] == ["day", "liu_yue"]

    # The natal-only/liu_nian-only interactions (午+未 combination, partial
    # 寅+午 three-harmony, 午+午 self-punishment, 寅+巳 harm) must not leak in.
    assert "three_harmony" not in by_type
    assert "harm" not in by_type


def test_analyze_liu_yue_day_master_stem_combination_detected():
    # Reuse 2026-08-14's already-verified Liu Yue pillar (丙申, from
    # test_bazi_math.py's Five Tigers rule tests) but with Day Master 辛
    # instead of 己 - 丙+辛 is a valid stem combination pair -> Water.
    pillars = _pillars("戊午", "辛未", "辛巳", "甲寅")  # Day Master 辛
    result = analyze_liu_yue(pillars, 2026, 8, 14)
    assert result["pillar"] == "丙申"
    combo = result["stem_combination_with_day_master"]
    assert combo is not None
    assert set(combo["stems"]) == {"丙", "辛"}
    assert combo["element"] == "Water"


# ---------------------------------------------------------------------------
# get_current_period - thin wrapper around analyze_liu_nian/analyze_liu_yue
# using today's real date, so it can't go stale. Tested structurally against
# today's actual date rather than a frozen one, since freezing would just
# re-test analyze_liu_nian/analyze_liu_yue's own already-covered logic.
# ---------------------------------------------------------------------------

def test_get_current_period_uses_todays_real_date():
    pillars = _pillars("戊午", "辛未", "己巳", "甲寅")
    today = date.today()
    result = get_current_period(pillars)

    assert result["liu_nian"] == analyze_liu_nian(pillars, today.year)
    assert result["liu_yue"] == analyze_liu_yue(pillars, today.year, today.month, today.day)
    assert result["liu_nian"]["year"] == today.year
    assert result["liu_yue"]["year"] == today.year
    assert result["liu_yue"]["month"] == today.month
