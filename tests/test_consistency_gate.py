"""Tests for core/consistency_gate.py - the cheap rule-based post-generation
check that flags reply text contradicting computed chart facts.
"""
from core.consistency_gate import check_consistency


def _strength(strength, favorable=None, unfavorable=None):
    return {
        "strength": strength,
        "favorable_elements": favorable or [],
        "unfavorable_elements": unfavorable or [],
    }


def test_no_facts_means_no_warnings():
    assert check_consistency("Your Day Master is strong and confident.", {}) == []


def test_flags_contradicting_strength_claim():
    facts = {"day_master_strength": _strength("weak")}
    reply = "Looking at your chart, your Day Master is strong this cycle."
    warnings = check_consistency(reply, facts)
    assert any("strong" in w and "weak" in w for w in warnings)


def test_matching_strength_claim_is_not_flagged():
    facts = {"day_master_strength": _strength("weak")}
    reply = "Your Day Master is weak, so Resource and Friend elements help you."
    assert check_consistency(reply, facts) == []


def test_flags_element_called_favorable_when_actually_unfavorable():
    facts = {"day_master_strength": _strength("weak", favorable=["Wood", "Water"], unfavorable=["Fire", "Metal"])}
    reply = "Fire is a favorable element for you this year."
    warnings = check_consistency(reply, facts)
    assert any("Fire" in w and "favorable" in w for w in warnings)


def test_flags_element_called_unfavorable_when_actually_favorable():
    facts = {"day_master_strength": _strength("weak", favorable=["Wood", "Water"], unfavorable=["Fire", "Metal"])}
    reply = "Water is unfavorable for someone with your chart."
    warnings = check_consistency(reply, facts)
    assert any("Water" in w and "unfavorable" in w for w in warnings)


def test_flags_invented_clash_when_no_interactions_detected():
    facts = {"branch_interactions": []}
    reply = "There's a clash between your Day and Hour branches that causes tension."
    warnings = check_consistency(reply, facts)
    assert any("clash" in w for w in warnings)


def test_does_not_flag_interaction_words_when_interactions_exist():
    facts = {"branch_interactions": [{"type": "clash", "branches": ["子", "午"]}]}
    reply = "There's a clash between your Day and Hour branches."
    assert check_consistency(reply, facts) == []


def test_flags_invented_stem_combination():
    facts = {"stem_combinations": []}
    reply = "Your Day Master stem combination with the Hour stem softens your temper."
    warnings = check_consistency(reply, facts)
    assert any("stem combination" in w for w in warnings)


def test_no_false_positive_on_unrelated_text():
    facts = {
        "day_master_strength": _strength("balanced"),
        "branch_interactions": [],
        "stem_combinations": [],
    }
    reply = "Bazi is a traditional Chinese metaphysical system based on your birth date and time."
    assert check_consistency(reply, facts) == []
