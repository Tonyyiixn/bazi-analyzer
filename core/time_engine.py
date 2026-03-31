from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from datetime import datetime, timedelta
import pytz

# Initialize these once so we don't restart them on every function call
geolocator = Nominatim(user_agent="bazi_app")
tf = TimezoneFinder()

def get_true_solar_time(year, month, day, hour, minute, city_name):
    """Converts standard clock time to True Solar Time based on longitude."""
    try:
        location = geolocator.geocode(city_name, timeout=10)
        if not location:
            return year, month, day, hour, minute
        
        lng = location.longitude
        lat = location.latitude
        tz_name = tf.timezone_at(lng=lng, lat=lat)
        tz = pytz.timezone(tz_name)
        
        birth_dt = tz.localize(datetime(year, month, day, hour, minute))
        utc_offset_hours = birth_dt.utcoffset().total_seconds() / 3600
        standard_meridian = utc_offset_hours * 15
        longitude_diff = lng - standard_meridian
        time_adjustment_minutes = longitude_diff * 4
        
        true_solar_dt = birth_dt + timedelta(minutes=time_adjustment_minutes)
        return true_solar_dt.year, true_solar_dt.month, true_solar_dt.day, true_solar_dt.hour, true_solar_dt.minute

    except (GeocoderTimedOut, GeocoderServiceError, Exception) as e:
        # If the external map API crashes entirely, we silently catch the error 
        # and return standard time so the user's Bazi chart still generates!
        print(f"Warning: Geocoder failed ({e}). Falling back to standard time.")
        return year, month, day, hour, minute