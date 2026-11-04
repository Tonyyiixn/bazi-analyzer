"""Tests for core/time_engine.py's True Solar Time correction.

The geocoder and timezone lookup are mocked in every test - the real
implementation hits the network (nominatim.openstreetmap.org), which we've
already seen be slow/flaky in dev. Mocking makes these tests fast,
deterministic, and independent of network state.
"""
from types import SimpleNamespace
from unittest.mock import patch

import core.time_engine as time_engine
from core.time_engine import get_true_solar_time


def test_falls_back_to_unmodified_time_when_geocode_returns_none():
    with patch.object(time_engine.geolocator, "geocode", return_value=None):
        result = get_true_solar_time(2000, 1, 1, 12, 0, "Nowhere")
    assert result == (2000, 1, 1, 12, 0)


def test_falls_back_to_unmodified_time_when_geocode_raises():
    with patch.object(time_engine.geolocator, "geocode", side_effect=Exception("network down")):
        result = get_true_solar_time(2000, 1, 1, 12, 0, "Somewhere")
    assert result == (2000, 1, 1, 12, 0)


def test_true_solar_time_correction_matches_hand_computed_value():
    """Longitude part only (equation of time off). Beijing: longitude 116.4074E, standard meridian for UTC+8 is 120E.
    diff = 116.4074 - 120 = -3.5926 degrees -> *4 = -14.3704 minutes.
    12:00:00 - 14m22.2s = 11:45:37.8, so .hour=11, .minute=45 exactly."""
    fake_location = SimpleNamespace(longitude=116.4074, latitude=39.9042)
    with patch.object(time_engine.geolocator, "geocode", return_value=fake_location), \
         patch.object(time_engine, "tf", SimpleNamespace(timezone_at=lambda **kw: "Asia/Shanghai")):
        year, month, day, hour, minute = get_true_solar_time(2000, 1, 1, 12, 0, "Beijing", include_equation_of_time=False)

    assert (year, month, day) == (2000, 1, 1)
    assert hour == 11
    assert minute == 45


def test_true_solar_time_correction_direction_east_vs_west_of_meridian():
    """A city east of its standard meridian should be adjusted forward
    (later); west of it, adjusted backward (earlier). Sanity check on sign,
    not exact magnitude."""
    east_of_meridian = SimpleNamespace(longitude=125.0, latitude=39.9042)  # east of 120E
    with patch.object(time_engine.geolocator, "geocode", return_value=east_of_meridian), \
         patch.object(time_engine, "tf", SimpleNamespace(timezone_at=lambda **kw: "Asia/Shanghai")):
        _, _, _, hour, minute = get_true_solar_time(2000, 1, 1, 12, 0, "EastCity", include_equation_of_time=False)
    # 125E is 5 degrees east of the 120E standard meridian -> +20 minutes
    assert (hour, minute) == (12, 20)

    west_of_meridian = SimpleNamespace(longitude=110.0, latitude=39.9042)  # west of 120E
    with patch.object(time_engine.geolocator, "geocode", return_value=west_of_meridian), \
         patch.object(time_engine, "tf", SimpleNamespace(timezone_at=lambda **kw: "Asia/Shanghai")):
        _, _, _, hour, minute = get_true_solar_time(2000, 1, 1, 12, 0, "WestCity", include_equation_of_time=False)
    # 110E is 10 degrees west of the 120E standard meridian -> -40 minutes
    assert (hour, minute) == (11, 20)


# VERIFIED: equation of time against almanac values (apparent minus mean
# solar time: about -14.2 min on Feb 11, +16.4 on Nov 3, -6.5 on Jul 26,
# ~0 on Apr 15). Spencer's series is good to about half a minute.
def test_equation_of_time_matches_almanac_values():
    from datetime import datetime, timezone
    for (month, day), expected in (((2, 11), -14.2), ((11, 3), 16.4), ((7, 26), -6.5), ((4, 15), 0.0)):
        eot = time_engine.equation_of_time_minutes(datetime(2024, month, day, 12, tzinfo=timezone.utc))
        assert abs(eot - expected) < 0.6, (month, day, eot)


def test_true_solar_time_includes_equation_of_time_by_default():
    """Same Beijing case as the hand-computed longitude test (11:45:38),
    plus the equation of time on Jan 1 (about -3 min) -> 11:42."""
    fake_location = SimpleNamespace(longitude=116.4074, latitude=39.9042)
    with patch.object(time_engine.geolocator, "geocode", return_value=fake_location), \
         patch.object(time_engine, "tf", SimpleNamespace(timezone_at=lambda **kw: "Asia/Shanghai")):
        assert get_true_solar_time(2000, 1, 1, 12, 0, "Beijing") == (2000, 1, 1, 11, 42)


def test_solar_term_clock_is_the_birth_instant_on_beijing_time():
    """06:00 EST in New York is 11:00 UTC is 19:00 Beijing time - the clock
    lunar_python's solar terms are on - regardless of local solar time."""
    ny = SimpleNamespace(longitude=-74.0060, latitude=40.7128)
    with patch.object(time_engine.geolocator, "geocode", return_value=ny), \
         patch.object(time_engine, "tf", SimpleNamespace(timezone_at=lambda **kw: "America/New_York")):
        result = time_engine.resolve_birth_time(2024, 2, 4, 6, 0, "New York")
    assert result["solar_term_clock"] == (2024, 2, 4, 19, 0)
    assert result["true_solar"][:3] == (2024, 2, 4)


def test_solar_term_clock_is_none_when_geocoding_fails():
    with patch.object(time_engine.geolocator, "geocode", return_value=None):
        result = time_engine.resolve_birth_time(2000, 1, 1, 12, 0, "Nowhere")
    assert result == {"true_solar": (2000, 1, 1, 12, 0), "solar_term_clock": None}
