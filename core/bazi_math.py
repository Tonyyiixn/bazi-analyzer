from lunar_python import Solar

def calculate_bazi_chart(year, month, day, hour, minute, gender_input):
    """Calculates the Four Pillars and Da Yun based on precise solar time."""
    solar_date = Solar.fromYmdHms(year, month, day, hour, minute, 0)
    lunar_date = solar_date.getLunar()
    bazi = lunar_date.getEightChar()
    
    gender_code = 1 if gender_input == "Male" else 0
    
    # Extract the pillars
    pillars = {
        "year": bazi.getYear(),
        "month": bazi.getMonth(),
        "day": bazi.getDay(),
        "hour": bazi.getTime()
    }
    
    # Extract the Da Yun (Luck Pillars)
    yun = bazi.getYun(gender_code)
    da_yuns = yun.getDaYun()
    
    return pillars, da_yuns