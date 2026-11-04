"""Independent reference for the Four Pillars - the gold source for the edge suite.

The other suites take gold from the engine, which can't catch the engine
being wrong. Edge cases are exactly where it might be, so this module
recomputes the pillars from first principles without lunar_python:

- Year / month: the Sun's apparent ecliptic longitude (PyEphem) at the
  absolute UTC instant of birth. Each jie (節) is a 30-degree step starting
  at 立春 = 315 degrees, and the year turns at 立春. Absolute time means a
  New York birth is compared against the same instant as a Beijing birth.
- Day: the Julian Day Number of the local apparent-solar date, anchored on
  1949-10-01 = 甲子. Day changes at 00:00 apparent solar time.
- Hour: local apparent solar time (longitude correction plus the equation
  of time - true solar time in the strict sense), 2-hour branches starting
  at 23:00. Zi-hour convention matches the engine's (lunar_python sect 2):
  23:00-23:59 keeps the current day pillar but takes the next day's stem
  for the hour.
- Clock time -> UTC goes through the IANA tz database (zoneinfo), so
  historical DST (e.g. China 1986-1991) is applied.

Precision: solar-term instants agree with published almanac times to about
a minute; the generator keeps every gold answer at least MIN_MARGIN_MIN
away from any boundary that decides it.

Self-check against lunar_python on ordinary charts:  python -m bench.reference
"""
import math
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import ephem

STEMS = "甲乙丙丁戊己庚辛壬癸"
BRANCHES = "子丑寅卯辰巳午未申酉戌亥"

# Jie (節) that start each Bazi month, by solar longitude. Month 0 is 寅.
JIE = ["立春", "驚蟄", "清明", "立夏", "芒種", "小暑", "立秋", "白露", "寒露", "立冬", "大雪", "小寒"]
LICHUN_LONGITUDE = 315.0
DEG_PER_MIN = 360 / 365.2422 / 1440  # mean solar motion, for margin estimates only

MIN_MARGIN_MIN = 5


def sexagenary(i):
    return STEMS[i % 10] + BRANCHES[i % 12]


def _ephem_date(utc):
    return ephem.Date(utc.replace(tzinfo=None))


def solar_longitude(utc):
    """The Sun's apparent geocentric ecliptic longitude (degrees, of date)."""
    d = _ephem_date(utc)
    sun = ephem.Sun(d)
    eq = ephem.Equatorial(sun.g_ra, sun.g_dec, epoch=d)
    return math.degrees(ephem.Ecliptic(eq, epoch=d).lon) % 360


def find_jie(month_index, year):
    """UTC instant of the jie that starts Bazi month `month_index` (0 = 寅)
    of Bazi year `year`, found by bisection on solar longitude."""
    target = (LICHUN_LONGITUDE + 30 * month_index) % 360
    # 立春 is ~Feb 4; each later jie ~30.4 days on.
    guess = datetime(year, 2, 4, tzinfo=timezone.utc) + timedelta(days=30.44 * month_index)
    lo, hi = guess - timedelta(days=4), guess + timedelta(days=4)

    def ahead(t):  # signed degrees the Sun is past the target
        return (solar_longitude(t) - target + 180) % 360 - 180

    for _ in range(40):  # 8 days / 2^40 is far below a second
        mid = lo + (hi - lo) / 2
        if ahead(mid) < 0:
            lo = mid
        else:
            hi = mid
    return lo


def apparent_solar_time(utc, longitude):
    """Local apparent solar time (naive datetime) and the equation of time
    in minutes (apparent minus mean), from the Sun's hour angle."""
    obs = ephem.Observer()
    obs.lon = str(longitude)
    obs.lat = "0"
    obs.elevation = 0
    obs.pressure = 0  # no refraction
    obs.date = _ephem_date(utc)
    sun = ephem.Sun(obs)
    hour_angle_h = math.degrees(float(obs.sidereal_time()) - float(sun.ra)) / 15
    mean = utc.replace(tzinfo=None) + timedelta(hours=longitude / 15)
    mean_h = mean.hour + mean.minute / 60 + mean.second / 3600
    apparent_h = (hour_angle_h + 12) % 24
    eot_min = ((apparent_h - mean_h + 12) % 24 - 12) * 60
    return mean + timedelta(minutes=eot_min), eot_min


def _minutes_to_hour_boundary(t):
    """Minutes from t to the nearest Bazi hour boundary (odd hours)."""
    m = (t.hour * 60 + t.minute + t.second / 60) % 120  # boundaries at 23:00, 01:00, ...
    since = (m - 60) % 120
    return min(since, 120 - since)


def _minutes_to_midnight(t):
    m = t.hour * 60 + t.minute + t.second / 60
    return min(m, 1440 - m)


def local_to_utc(year, month, day, hour, minute, tz_name):
    """UTC for a local clock time, or None if that clock time doesn't exist
    or happens twice (a DST transition) - such births are ambiguous."""
    tz = ZoneInfo(tz_name)
    naive = datetime(year, month, day, hour, minute)
    a = naive.replace(tzinfo=tz, fold=0).astimezone(timezone.utc)
    b = naive.replace(tzinfo=tz, fold=1).astimezone(timezone.utc)
    if a != b or a.astimezone(tz).replace(tzinfo=None) != naive:
        return None
    return a


def pillars(year, month, day, hour, minute, tz_name, longitude, equation_of_time=True):
    """Four pillars for a local clock time, plus the margins (minutes) to
    each boundary that decides them, for the generator to filter on.
    equation_of_time=False uses mean solar time instead (what the engine
    does today), so the generator can tell which cases the equation of time
    decides. Returns None for an ambiguous or nonexistent clock time."""
    utc = local_to_utc(year, month, day, hour, minute, tz_name)
    if utc is None:
        return None

    lam = solar_longitude(utc)
    month_index = int(((lam - LICHUN_LONGITUDE) % 360) // 30)
    bazi_year = utc.year - 1 if (utc.month <= 2 and month_index >= 10) else utc.year
    year_idx = (bazi_year - 4) % 60
    month_stem = ([2, 4, 6, 8, 0][year_idx % 10 % 5] + month_index) % 10
    month_branch = (2 + month_index) % 12

    apparent, eot_min = apparent_solar_time(utc, longitude)
    if not equation_of_time:
        apparent -= timedelta(minutes=eot_min)
        eot_min = 0.0
    jdn = apparent.date().toordinal() + 1721425
    day_idx = (jdn - 2433191) % 60  # 1949-10-01 (JDN 2433191) is 甲子

    branch = ((apparent.hour + 1) // 2) % 12
    stem_day = (day_idx + 1) % 10 if apparent.hour == 23 else day_idx % 10  # sect 2: late zi uses next day's stem
    hour_stem = ([0, 2, 4, 6, 8][stem_day % 5] + branch) % 10

    to_term = (lam - LICHUN_LONGITUDE) % 30
    return {
        "pillars": {
            "year": sexagenary(year_idx),
            "month": STEMS[month_stem] + BRANCHES[month_branch],
            "day": sexagenary(day_idx),
            "hour": STEMS[hour_stem] + BRANCHES[branch],
        },
        "utc": utc.strftime("%Y-%m-%d %H:%M"),
        "solar_time": apparent.strftime("%Y-%m-%d %H:%M"),
        "mean_solar_time": (apparent - timedelta(minutes=eot_min)).strftime("%Y-%m-%d %H:%M"),
        "equation_of_time_min": round(eot_min, 1),
        "solar_longitude": round(lam, 3),
        "margins_min": {
            "jie": round(min(to_term, 30 - to_term) / DEG_PER_MIN),
            "hour": round(_minutes_to_hour_boundary(apparent), 1),
            "day": round(_minutes_to_midnight(apparent), 1),
        },
    }


# ---------------------------------------------------------------- self-check

def _self_check():
    """Agreement with lunar_python where the two methods should agree:
    solar-term instants (Beijing time) and the day pillar, plus the
    equation of time against known values."""
    from lunar_python import Solar

    simplified = {"驚蟄": "惊蛰", "芒種": "芒种"}
    beijing = timezone(timedelta(hours=8))  # lunar_python's tables are UTC+8 year-round (no 1986-91 DST)
    worst = 0.0
    for y in (1950, 1975, 1990, 2000, 2024, 2030):
        table = Solar.fromYmd(y, 6, 1).getLunar().getJieQiTable()
        for i, name in enumerate(JIE[:11]):  # 小寒 belongs to the next solar year
            ours = find_jie(i, y).astimezone(beijing)
            theirs = table[simplified.get(name, name)]
            theirs = datetime(theirs.getYear(), theirs.getMonth(), theirs.getDay(),
                              theirs.getHour(), theirs.getMinute(), theirs.getSecond(), tzinfo=beijing)
            worst = max(worst, abs((ours - theirs).total_seconds()) / 60)
    print(f"jie instants vs lunar_python, 66 terms: worst difference {worst:.2f} min")

    mismatches = 0
    for n in range(400):
        d = date(1950, 1, 1) + timedelta(days=n * 61)
        ours = sexagenary((d.toordinal() + 1721425 - 2433191) % 60)
        theirs = Solar.fromYmdHms(d.year, d.month, d.day, 12, 0, 0).getLunar().getEightChar().getDay()
        mismatches += ours != theirs
    print(f"day pillar vs lunar_python, 400 dates 1950-2016: {mismatches} mismatches")

    for d, expected in ((datetime(2024, 2, 11, 12), -14.2), (datetime(2024, 11, 3, 12), 16.4),
                        (datetime(2024, 7, 26, 12), -6.5), (datetime(2024, 4, 15, 12), 0.0)):
        _, eot = apparent_solar_time(d.replace(tzinfo=timezone.utc), 0.0)
        print(f"equation of time {d:%Y-%m-%d}: {eot:+.1f} min (almanac ~{expected:+.1f})")


if __name__ == "__main__":
    _self_check()
