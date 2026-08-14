"""Tests for core/guardrails.py - the high-stakes question guardrail.
"""
from core.guardrails import build_guardrail_instructions, check_guardrail_compliance, detect_categories


def test_detects_self_harm_language():
    assert detect_categories("I don't know what to do, I want to kill myself.") == ["self_harm"]


def test_detects_mortality_question():
    assert detect_categories("Can you tell me when will I die based on my chart?") == ["mortality"]


def test_detects_medical_diagnosis_question():
    assert detect_categories("Doctor said tests are pending, do I have cancer according to my chart?") == ["medical_diagnosis"]


def test_detects_major_decision_question():
    assert detect_categories("Should I divorce my husband this year?") == ["major_irreversible_decision"]


def test_ordinary_message_detects_nothing():
    assert detect_categories("What does my Day Master say about my career?") == []


def test_can_detect_multiple_categories_at_once():
    categories = detect_categories("Should I quit my job, and also do I have cancer?")
    assert set(categories) == {"major_irreversible_decision", "medical_diagnosis"}


def test_build_instructions_empty_for_no_categories():
    assert build_guardrail_instructions([]) == ""


def test_build_instructions_includes_category_text():
    text = build_guardrail_instructions(["self_harm"])
    assert "988" in text
    assert "SAFETY INSTRUCTIONS" in text


def test_compliance_check_flags_missing_markers():
    warnings = check_guardrail_compliance("Your Fire element is strong this year.", ["self_harm"])
    assert len(warnings) == 1
    assert "self_harm" in warnings[0]


def test_compliance_check_passes_when_marker_present():
    reply = "I hear you, and I want to encourage you to reach out to a crisis line like 988 or a mental health professional."
    assert check_guardrail_compliance(reply, ["self_harm"]) == []


def test_compliance_check_no_categories_no_warnings():
    assert check_guardrail_compliance("Anything at all.", []) == []
