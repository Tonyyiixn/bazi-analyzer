from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from datetime import datetime, timedelta, timezone
import math
import pytz

# Initialize these once so we don't restart them on every function call
geolocator = Nominatim(user_agent="bazi_app")
tf = TimezoneFinder()

# lunar_python's solar-term tables are in Beijing standard time, year-round
# (no 1986-1991 DST), so the year/month pillars must be decided by the birth
# instant expressed on that clock - not by the local solar time.
SOLAR_TERM_CLOCK = timezone(timedelta(hours=8))


def equation_of_time_minutes(utc_dt):
    """Apparent minus mean solar time, in minutes (between about -14 in
    February and +16 in November). Spencer's (1971) series - accurate to
    within about half a minute, which is plenty for 2-hour Bazi branches."""
    day_of_year = utc_dt.timetuple().tm_yday
    gamma = 2 * math.pi / 365 * (day_of_year - 1 + (utc_dt.hour - 12) / 24)
    return 229.18 * (0.000075 + 0.001868 * math.cos(gamma) - 0.032077 * math.sin(gamma)
                     - 0.014615 * math.cos(2 * gamma) - 0.040849 * math.sin(2 * gamma))


def resolve_birth_time(year, month, day, hour, minute, city_name, include_equation_of_time=True):
    """Both clocks a chart needs, from a local clock time and city:

    - "true_solar": local true solar time (longitude correction, plus the
      equation of time unless include_equation_of_time=False) - decides the
      day and hour pillars.
    - "solar_term_clock": the same instant on Beijing standard time - decides
      the year and month pillars (and Da Yun timing), because those turn at
      absolute solar-term instants. None if the city couldn't be resolved.

    Each is a (year, month, day, hour, minute) tuple. Falls back to the clock
    time as given (and no solar-term clock) if geocoding fails."""
    fallback = {"true_solar": (year, month, day, hour, minute), "solar_term_clock": None}
    try:
        location = geolocator.geocode(city_name, timeout=4)
        if not location:
            return fallback

        lng = location.longitude
        lat = location.latitude
        tz_name = tf.timezone_at(lng=lng, lat=lat)
        tz = pytz.timezone(tz_name)

        birth_dt = tz.localize(datetime(year, month, day, hour, minute))
        utc_offset_hours = birth_dt.utcoffset().total_seconds() / 3600
        standard_meridian = utc_offset_hours * 15
        longitude_diff = lng - standard_meridian
        time_adjustment_minutes = longitude_diff * 4
        if include_equation_of_time:
            time_adjustment_minutes += equation_of_time_minutes(birth_dt.astimezone(timezone.utc))

        true_solar_dt = birth_dt + timedelta(minutes=time_adjustment_minutes)
        term_dt = birth_dt.astimezone(SOLAR_TERM_CLOCK)
        return {
            "true_solar": (true_solar_dt.year, true_solar_dt.month, true_solar_dt.day,
                           true_solar_dt.hour, true_solar_dt.minute),
            "solar_term_clock": (term_dt.year, term_dt.month, term_dt.day, term_dt.hour, term_dt.minute),
        }

    except (GeocoderTimedOut, GeocoderServiceError, Exception) as e:
        # If the external map API crashes entirely, we silently catch the error
        # and return standard time so the user's Bazi chart still generates!
        print(f"Warning: Geocoder failed ({e}). Falling back to standard time.")
        return fallback


def get_true_solar_time(year, month, day, hour, minute, city_name, include_equation_of_time=True):
    """Converts standard clock time to True Solar Time (longitude plus the
    equation of time). Prefer resolve_birth_time when building a chart - the
    year/month pillars need the solar-term clock it also returns."""
    return resolve_birth_time(year, month, day, hour, minute, city_name, include_equation_of_time)["true_solar"]
