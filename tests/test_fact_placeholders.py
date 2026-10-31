"""Tests for core/fact_placeholders.py - filling {{placeholder}} tokens in
the model's reply from tool-computed chart facts.
"""
from core.fact_placeholders import UNAVAILABLE, render_fact_placeholders


def _facts(strength, favorable=None, unfavorable=None):
    return {"day_master_strength": {
        "strength": strength,
        "favorable_elements": favorable or [],
        "unfavorable_elements": unfavorable or [],
    }}


def test_fills_strength_and_element_lists():
    facts = _facts("weak", favorable=["Water", "Metal"], unfavorable=["Wood", "Fire", "Earth"])
    text, warnings = render_fact_placeholders(
        "Your Day Master is {{day_master_strength}}. {{favorable_elements}} help; "
        "{{unfavorable_elements}} drain you.",
        facts,
    )
    assert text == "Your Day Master is weak. Water and Metal help; Wood, Fire and Earth drain you."
    assert warnings == []


def test_tolerates_whitespace_inside_braces():
    text, _ = render_fact_placeholders("{{ day_master_strength }}", _facts("strong"))
    assert text == "strong"


def test_single_element_and_empty_list():
    text, _ = render_fact_placeholders(
        "{{favorable_elements}} / {{unfavorable_elements}}", _facts("strong", favorable=["Fire"])
    )
    assert text == "Fire / none"


def test_placeholder_without_computed_fact_warns_and_never_leaks_braces():
    text, warnings = render_fact_placeholders("Your Day Master is {{day_master_strength}}.", {})
    assert text == f"Your Day Master is {UNAVAILABLE}."
    assert len(warnings) == 1 and "day_master_strength" in warnings[0]


def test_unknown_placeholder_warns():
    text, warnings = render_fact_placeholders("{{lucky_number}}", _facts("strong"))
    assert text == UNAVAILABLE
    assert "lucky_number" in warnings[0]


def test_text_without_placeholders_is_unchanged():
    reply = "Bazi reads your birth moment as four pillars."
    assert render_fact_placeholders(reply, _facts("strong")) == (reply, [])
