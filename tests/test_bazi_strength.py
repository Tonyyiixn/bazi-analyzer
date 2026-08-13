"""Tests for core/bazi_strength.py - Day Master strength scoring.

IMPORTANT DISTINCTION FROM OTHER TEST FILES: these tests verify the 扶抑
scoring algorithm's OWN internal logic is implemented as specified (every
weight hand-tallied below before running the code), not that this is the
objectively "correct" reading of a chart - 用神 selection is a genuine,
documented judgment call (see core/bazi_strength.py's module docstring),
not an independently verifiable fact like the Ten God table or the 60-year
cycle epoch.
"""
from core.bazi_strength import analyze_day_master_strength


def _pillars(year, month, day, hour):
    return {"year": year, "month": month, "day": day, "hour": hour}


def test_weak_day_master_hand_tallied_example():
    # Day Master 甲 (Wood). Hand-tallied weights:
    #   year_stem  庚 -> Seven Killings (drain, w1)
    #   year_branch 申(main qi 庚) -> Seven Killings (drain, w1)
    #   month_stem 丙 -> Eating God (drain, w1)
    #   month_branch 午(main qi 丁) -> Hurting Officer (drain, w2 - 得令)
    #   day_branch 子(main qi 癸) -> Direct Resource (support, w1)
    #   hour_stem 戊 -> Indirect Wealth (drain, w1)
    #   hour_branch 辰(main qi 戊) -> Indirect Wealth (drain, w1)
    # support=1, drain=7 -> weak
    pillars = _pillars("庚申", "丙午", "甲子", "戊辰")
    result = analyze_day_master_strength(pillars)

    assert result["day_master"] == "甲"
    assert result["day_master_element"] == "Wood"
    assert result["support_weight"] == 1
    assert result["drain_weight"] == 7
    assert result["strength"] == "weak"
    assert result["note"] is None

    # Weak Day Master wants itself + its Resource element
    assert set(result["favorable_elements"]) == {"Wood", "Water"}
    assert set(result["unfavorable_elements"]) == {"Fire", "Earth", "Metal"}


def test_strong_day_master_hand_tallied_example():
    # Day Master 甲 (Wood). Hand-tallied weights:
    #   year_stem  乙 -> Rob Wealth (support, w1)
    #   year_branch 寅(main qi 甲) -> Friend (support, w1)
    #   month_stem 癸 -> Direct Resource (support, w1)
    #   month_branch 亥(main qi 壬) -> Indirect Resource (support, w2 - 得令)
    #   day_branch 寅(main qi 甲) -> Friend (support, w1)
    #   hour_stem 丙 -> Eating God (drain, w1)
    #   hour_branch 午(main qi 丁) -> Hurting Officer (drain, w1)
    # support=6, drain=2 -> strong
    pillars = _pillars("乙寅", "癸亥", "甲寅", "丙午")
    result = analyze_day_master_strength(pillars)

    assert result["support_weight"] == 6
    assert result["drain_weight"] == 2
    assert result["strength"] == "strong"

    # Strong Day Master wants to be drained/controlled: Output, Wealth, Officer
    assert set(result["favorable_elements"]) == {"Fire", "Earth", "Metal"}
    assert set(result["unfavorable_elements"]) == {"Wood", "Water"}


def test_balanced_day_master_hand_tallied_example():
    # Day Master 甲 (Wood). Hand-tallied weights:
    #   year_stem  乙 -> Rob Wealth (support, w1)
    #   year_branch 申(main qi 庚) -> Seven Killings (drain, w1)
    #   month_stem 丙 -> Eating God (drain, w1)
    #   month_branch 亥(main qi 壬) -> Indirect Resource (support, w2 - 得令)
    #   day_branch 子(main qi 癸) -> Direct Resource (support, w1)
    #   hour_stem 戊 -> Indirect Wealth (drain, w1)
    #   hour_branch 辰(main qi 戊) -> Indirect Wealth (drain, w1)
    # support = 1+2+1 = 4, drain = 1+1+1+1 = 4 -> balanced
    pillars = _pillars("乙申", "丙亥", "甲子", "戊辰")
    result = analyze_day_master_strength(pillars)

    assert result["support_weight"] == 4
    assert result["drain_weight"] == 4
    assert result["strength"] == "balanced"
    assert result["favorable_elements"] == []
    assert result["unfavorable_elements"] == []
    assert result["note"] is not None


def test_favorable_and_unfavorable_elements_partition_all_five_when_skewed():
    """For any non-balanced result, favorable + unfavorable should together
    cover all five elements exactly once - no element should be omitted or
    double-counted."""
    weak_pillars = _pillars("庚申", "丙午", "甲子", "戊辰")
    result = analyze_day_master_strength(weak_pillars)
    all_elements = set(result["favorable_elements"]) | set(result["unfavorable_elements"])
    assert all_elements == {"Wood", "Fire", "Earth", "Metal", "Water"}
    assert len(result["favorable_elements"]) + len(result["unfavorable_elements"]) == 5


def test_factors_breakdown_has_seven_characters_with_correct_weights():
    pillars = _pillars("庚申", "丙午", "甲子", "戊辰")
    result = analyze_day_master_strength(pillars)
    factors = result["factors"]
    assert len(factors) == 7

    positions_to_weight = {f["position"]: f["weight"] for f in factors}
    assert positions_to_weight["month_branch"] == 2  # 得令 double weight
    for position in ("year_stem", "year_branch", "month_stem", "day_branch", "hour_stem", "hour_branch"):
        assert positions_to_weight[position] == 1

    # Every factor's category must agree with its own ten_god classification
    from core.bazi_strength import SUPPORT_TEN_GODS, DRAIN_TEN_GODS
    for f in factors:
        if f["ten_god"] in SUPPORT_TEN_GODS:
            assert f["category"] == "support"
        elif f["ten_god"] in DRAIN_TEN_GODS:
            assert f["category"] == "drain"


def test_method_is_labeled_explicitly():
    pillars = _pillars("庚申", "丙午", "甲子", "戊辰")
    result = analyze_day_master_strength(pillars)
    assert "扶抑" in result["method"]
