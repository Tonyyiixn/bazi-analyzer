"""Deterministic tests for core/bazi_math.py.

Two tiers, clearly separated:

- VERIFIED tests assert against facts independently confirmable without a
  professional calculator: the 60-year sexagenary cycle epoch (1984 = Jia-Zi
  is a well-established reference point cited across Chinese calendar
  sources), and standard Ten God theory (universally taught the same way
  across schools, unlike 用神-selection methodology which genuinely varies).
- REGRESSION BASELINE tests just pin down current output so refactors don't
  silently change results. They are NOT proof of correctness - if you have
  a professional calculator you trust, please spot-check these against it.
"""
import pytest

from core.bazi_math import (
    calculate_bazi_chart,
    get_element_counts,
    get_ten_god,
    calculate_chart_ten_gods,
    STEM_ATTRIBUTES,
    BRANCH_MAIN_QI,
)

ALL_STEMS = ['甲', '乙', '丙', '丁', '戊', '己', '庚', '辛', '壬', '癸']
ALL_BRANCHES = ['子', '丑', '寅', '卯', '辰', '巳', '午', '未', '申', '酉', '戌', '亥']


# ---------------------------------------------------------------------------
# VERIFIED: sexagenary cycle epoch (60-year repeat)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("year", [1924, 1984, 2044])
def test_jiazi_epoch_years_have_jiazi_year_pillar(year):
    """1984 is the standard-reference Jia-Zi (甲子) year; the cycle repeats
    every 60 years, so 1924 and 2044 must also be Jia-Zi. Using June 15 to
    stay well clear of the 立春 (~Feb 4) year-boundary and any lunar new
    year ambiguity near Jan/Feb."""
    pillars, _ = calculate_bazi_chart(year, 6, 15, 12, 0, "Male")
    assert pillars["year"] == "甲子"


def test_year_pillar_cycles_every_60_years():
    """Any two years 60 apart must share the same year pillar, for any
    starting point (not just the Jia-Zi epoch)."""
    base_pillars, _ = calculate_bazi_chart(1990, 6, 15, 12, 0, "Male")
    shifted_pillars, _ = calculate_bazi_chart(1990 + 60, 6, 15, 12, 0, "Male")
    assert base_pillars["year"] == shifted_pillars["year"]


# ---------------------------------------------------------------------------
# VERIFIED: Ten God theory is standardized (unlike 用神 method, this part of
# Bazi theory does not vary by school). Tables below are hand-derived from
# the generating/controlling cycles, independently of get_ten_god()'s code.
# ---------------------------------------------------------------------------

# Day Master 甲 (Yang Wood) vs each of the 10 stems.
EXPECTED_TEN_GODS_FROM_JIA = {
    '甲': 'Friend', '乙': 'Rob Wealth',
    '丙': 'Eating God', '丁': 'Hurting Officer',
    '戊': 'Indirect Wealth', '己': 'Direct Wealth',
    '庚': 'Seven Killings', '辛': 'Direct Officer',
    '壬': 'Indirect Resource', '癸': 'Direct Resource',
}

# Day Master 癸 (Yin Water) vs each of the 10 stems - covers a different
# element and the opposite (Yin) polarity as a cross-check.
EXPECTED_TEN_GODS_FROM_GUI = {
    '癸': 'Friend', '壬': 'Rob Wealth',
    '乙': 'Eating God', '甲': 'Hurting Officer',
    '丁': 'Indirect Wealth', '丙': 'Direct Wealth',
    '己': 'Seven Killings', '戊': 'Direct Officer',
    '辛': 'Indirect Resource', '庚': 'Direct Resource',
}


@pytest.mark.parametrize("target,expected", EXPECTED_TEN_GODS_FROM_JIA.items())
def test_ten_god_from_jia_day_master(target, expected):
    assert get_ten_god('甲', target) == expected


@pytest.mark.parametrize("target,expected", EXPECTED_TEN_GODS_FROM_GUI.items())
def test_ten_god_from_gui_day_master(target, expected):
    assert get_ten_god('癸', target) == expected


def test_ten_god_unknown_for_invalid_input():
    # get_ten_god looks up element/polarity for whatever character it's given
    # (STEM_ATTRIBUTES covers both stems and branches), so only a character
    # outside that table entirely is genuinely invalid.
    assert get_ten_god('甲', 'not-a-real-character') == 'Unknown'
    assert get_ten_god('not-a-real-character', '甲') == 'Unknown'


# ---------------------------------------------------------------------------
# VERIFIED: pure structural/counting logic, no external reference needed
# ---------------------------------------------------------------------------

def test_element_counts_pure_synthetic_chart():
    # 甲子 x4 = 4x (Wood stem + Water branch)
    pillars = {"year": "甲子", "month": "甲子", "day": "甲子", "hour": "甲子"}
    counts = get_element_counts(pillars)
    assert counts == {"Wood": 4, "Fire": 0, "Earth": 0, "Metal": 0, "Water": 4}


def test_element_counts_all_five_present():
    pillars = {"year": "甲午", "month": "戊申", "day": "壬子", "hour": "乙丑"}
    counts = get_element_counts(pillars)
    assert set(counts.keys()) == {"Wood", "Fire", "Earth", "Metal", "Water"}
    assert sum(counts.values()) == 8  # 4 pillars x 2 chars


def test_branch_main_qi_covers_all_12_branches_with_valid_stems():
    assert set(BRANCH_MAIN_QI.keys()) == set(ALL_BRANCHES)
    for branch, stem in BRANCH_MAIN_QI.items():
        assert stem in STEM_ATTRIBUTES, f"{branch} -> {stem} is not a valid stem"


def test_stem_attributes_covers_all_stems_and_branches():
    assert set(STEM_ATTRIBUTES.keys()) == set(ALL_STEMS) | set(ALL_BRANCHES)
    for char, attrs in STEM_ATTRIBUTES.items():
        assert attrs['element'] in {'Wood', 'Fire', 'Earth', 'Metal', 'Water'}
        assert attrs['polarity'] in {'Yang', 'Yin'}


def test_calculate_chart_ten_gods_day_stem_is_always_day_master():
    pillars = {"year": "甲午", "month": "戊申", "day": "壬子", "hour": "乙丑"}
    result = calculate_chart_ten_gods(pillars)
    assert result['day']['stem'] == 'Day Master'


def test_calculate_chart_ten_gods_branch_uses_main_qi():
    pillars = {"year": "甲午", "month": "戊申", "day": "壬子", "hour": "乙丑"}
    result = calculate_chart_ten_gods(pillars)
    day_master = pillars['day'][0]
    for key in ('year', 'month', 'hour'):
        branch = pillars[key][1]
        expected = get_ten_god(day_master, BRANCH_MAIN_QI[branch])
        assert result[key]['branch'] == expected


def test_calculate_chart_ten_gods_handles_malformed_input_gracefully():
    result = calculate_chart_ten_gods({"year": "", "month": "", "day": "", "hour": ""})
    assert result['day']['stem'] == 'Day Master'
    assert result['year'] == {'stem': 'N/A', 'branch': 'N/A'}


# ---------------------------------------------------------------------------
# Gender wiring sanity check (catches a swapped Male/Female mapping, without
# asserting exact forward/backward cycle direction)
# ---------------------------------------------------------------------------

def test_male_and_female_da_yun_sequences_differ():
    male_pillars, male_da_yuns = calculate_bazi_chart(1990, 6, 15, 12, 0, "Male")
    female_pillars, female_da_yuns = calculate_bazi_chart(1990, 6, 15, 12, 0, "Female")
    # Same birth moment -> identical natal chart...
    assert male_pillars == female_pillars
    # ...but gender flips Da Yun direction, so the luck-pillar sequence
    # (aside from possibly the same first entry) should differ.
    male_sequence = [d['pillar'] for d in male_da_yuns]
    female_sequence = [d['pillar'] for d in female_da_yuns]
    assert male_sequence != female_sequence


def test_gender_string_aliases_are_equivalent():
    pillars_full, da_yuns_full = calculate_bazi_chart(1990, 6, 15, 12, 0, "Male")
    pillars_short, da_yuns_short = calculate_bazi_chart(1990, 6, 15, 12, 0, "M")
    assert pillars_full == pillars_short
    assert [d['pillar'] for d in da_yuns_full] == [d['pillar'] for d in da_yuns_short]


# ---------------------------------------------------------------------------
# REGRESSION BASELINE - current output, NOT independently verified against a
# professional calculator. If you check these against a trusted source and
# find a mismatch, that's a real bug to fix, not a test to "correct".
# ---------------------------------------------------------------------------

def test_regression_baseline_1990_06_15_1230_male():
    pillars, da_yuns = calculate_bazi_chart(1990, 6, 15, 12, 30, "Male")
    assert pillars == {"year": "庚午", "month": "壬午", "day": "辛亥", "hour": "甲午"}
    # NOTE: index 0 is a "birth to first Da Yun" placeholder with an empty
    # pillar (lunar_python's own behavior) - the first real luck pillar is
    # index 1. The frontend currently renders da_yuns[] unfiltered, so this
    # blank entry likely shows as an empty card - worth a separate look.
    assert da_yuns[0]["pillar"] == ""
    assert da_yuns[1]["pillar"] == "癸未"


def test_regression_baseline_1995_08_24_1645_female():
    pillars, da_yuns = calculate_bazi_chart(1995, 8, 24, 16, 45, "Female")
    assert pillars == {"year": "乙亥", "month": "甲申", "day": "丁亥", "hour": "戊申"}
    assert da_yuns[0]["pillar"] == ""
    assert da_yuns[1]["pillar"] == "乙酉"
