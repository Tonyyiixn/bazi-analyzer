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

def get_element_counts(pillars):
    """Counts the frequency of the Five Elements in the Natal Chart."""
    # The master legend of Wu Xing (Five Elements) characters
    elements_map = {
        "Wood": ["甲", "乙", "寅", "卯"],
        "Fire": ["丙", "丁", "巳", "午"],
        "Earth": ["戊", "己", "辰", "戌", "丑", "未"],
        "Metal": ["庚", "辛", "申", "酉"],
        "Water": ["壬", "癸", "亥", "子"]
    }
    
    # Start with a baseline of zero for everything
    counts = {"Wood": 0, "Fire": 0, "Earth": 0, "Metal": 0, "Water": 0}
    
    # Combine all 8 characters from the user's pillars into one long string
    bazi_chars = pillars['year'] + pillars['month'] + pillars['day'] + pillars['hour']
    
    # Iterate through the characters and increment the matching element counter
    for char in bazi_chars:
        for element, chars in elements_map.items():
            if char in chars:
                counts[element] += 1
                
    return counts