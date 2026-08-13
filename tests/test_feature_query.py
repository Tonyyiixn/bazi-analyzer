"""Tests for core/feature_query.py - building a principle-search query from
a chart's already-computed features (not the agent's free text).
"""
from core.bazi_math import calculate_chart_ten_gods
from core.bazi_interactions import find_branch_interactions, find_stem_combinations
from core.bazi_strength import analyze_day_master_strength
from core.feature_query import build_principle_query


def _pillars(year, month, day, hour):
    return {"year": year, "month": month, "day": day, "hour": hour}


def test_query_includes_strength_method_and_ten_gods():
    # Same weak Day Master example as test_bazi_strength.py's hand-tallied case.
    pillars = _pillars("庚申", "丙午", "甲子", "戊辰")
    ten_gods = calculate_chart_ten_gods(pillars)
    branch_interactions = find_branch_interactions(pillars)
    stem_combinations = find_stem_combinations(pillars)
    day_master_strength = analyze_day_master_strength(pillars)

    query = build_principle_query(ten_gods, branch_interactions, stem_combinations, day_master_strength)

    assert "Day Master weak strength" in query
    assert "Support/Suppress" in query or day_master_strength["method"] in query
    assert "favorable Wood" in query
    assert "favorable Water" in query
    assert "unfavorable Fire" in query
    # Ten Gods present on non-Day-Master characters should be included verbatim.
    assert "Seven Killings" in query
    assert "Hurting Officer" in query
    # "Day Master" placeholder itself must not leak in as a bogus Ten God term.
    assert query.count("Day Master") == 1


def test_query_includes_branch_interactions_and_stem_combinations():
    # 子午 clash (day vs month branch), plus a stem combination case.
    pillars = _pillars("甲子", "丙午", "甲午", "己巳")
    ten_gods = calculate_chart_ten_gods(pillars)
    branch_interactions = find_branch_interactions(pillars)
    stem_combinations = find_stem_combinations(pillars)
    day_master_strength = analyze_day_master_strength(pillars)

    query = build_principle_query(ten_gods, branch_interactions, stem_combinations, day_master_strength)

    assert any(it["type"] == "clash" for it in branch_interactions)
    assert "clash chong" in query
    # 甲己 combination between day and hour stems, involving the Day Master.
    assert any(c.get("involves_day_master") for c in stem_combinations)
    assert "stem combination" in query
    assert "Day Master combination" in query


def test_query_handles_balanced_chart_with_no_interactions():
    pillars = _pillars("甲子", "乙丑", "甲寅", "乙丑")
    ten_gods = calculate_chart_ten_gods(pillars)
    branch_interactions = find_branch_interactions(pillars)
    stem_combinations = find_stem_combinations(pillars)
    day_master_strength = analyze_day_master_strength(pillars)

    # Should not raise even when both lists are empty.
    query = build_principle_query(ten_gods, branch_interactions, stem_combinations, day_master_strength)
    assert isinstance(query, str)
    assert day_master_strength["strength"] in query
