from lunar_python import Solar

def calculate_bazi_chart(year, month, day, hour, minute, gender_input):
    """Calculates the Four Pillars and Da Yun based on precise solar time."""
    solar_date = Solar.fromYmdHms(year, month, day, hour, minute, 0)
    lunar_date = solar_date.getLunar()
    bazi = lunar_date.getEightChar()
    
    gender_code = 1 if gender_input in ["Male", "M"] else 0
    
    # Extract the pillars
    pillars = {
        "year": bazi.getYear(),
        "month": bazi.getMonth(),
        "day": bazi.getDay(),
        "hour": bazi.getTime()
    }
    
    # Extract the Da Yun (Luck Pillars)
    yun = bazi.getYun(gender_code)
    raw_da_yuns = yun.getDaYun()
    
    clean_da_yuns = []
    # We loop through the objects and only pull the exact strings/ints we need.
    # We also limit it to the first 10 cycles (approx 100 years of life).
    for i, dy in enumerate(raw_da_yuns):
        if i >= 10: 
            break
            
        clean_da_yuns.append({
            "start_age": dy.getStartAge(),
            "start_year": dy.getStartYear(),
            "pillar": dy.getGanZhi()
        })
    
    return pillars, clean_da_yuns

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


# Heavenly Stems with their Element and Polarity (Yin/Yang)
STEM_ATTRIBUTES = {
    '甲': {'element': 'Wood', 'polarity': 'Yang'},
    '乙': {'element': 'Wood', 'polarity': 'Yin'},
    '丙': {'element': 'Fire', 'polarity': 'Yang'},
    '丁': {'element': 'Fire', 'polarity': 'Yin'},
    '戊': {'element': 'Earth', 'polarity': 'Yang'},
    '己': {'element': 'Earth', 'polarity': 'Yin'},
    '庚': {'element': 'Metal', 'polarity': 'Yang'},
    '辛': {'element': 'Metal', 'polarity': 'Yin'},
    '壬': {'element': 'Water', 'polarity': 'Yang'},
    '癸': {'element': 'Water', 'polarity': 'Yin'},
    '寅': {'element': 'Wood', 'polarity': 'Yang'},
    '卯': {'element': 'Wood', 'polarity': 'Yin'},
    '辰': {'element': 'Earth', 'polarity': 'Yang'},
    '巳': {'element': 'Fire', 'polarity': 'Yin'},
    '午': {'element': 'Fire', 'polarity': 'Yang'},
    '未': {'element': 'Earth', 'polarity': 'Yin'},
    '申': {'element': 'Metal', 'polarity': 'Yang'},
    '酉': {'element': 'Metal', 'polarity': 'Yin'},
    '戌': {'element': 'Earth', 'polarity': 'Yang'},
    '亥': {'element': 'Water', 'polarity': 'Yin'},
    '子': {'element': 'Water', 'polarity': 'Yang'},
}

def get_ten_god(day_master_stem, target_stem):
    """Calculates the Shishen (Ten God) relationship between the Day Master and another Stem."""
    if target_stem not in STEM_ATTRIBUTES or day_master_stem not in STEM_ATTRIBUTES:
        return "Unknown"

    dm = STEM_ATTRIBUTES[day_master_stem]
    target = STEM_ATTRIBUTES[target_stem]
    
    same_polarity = dm['polarity'] == target['polarity']
    
    # 1. Same Element (Companions)
    if dm['element'] == target['element']:
        return "Friend" if same_polarity else "Rob Wealth"
        
    # 2. Output (Day Master produces Target)
    output_cycle = {'Wood': 'Fire', 'Fire': 'Earth', 'Earth': 'Metal', 'Metal': 'Water', 'Water': 'Wood'}
    if output_cycle[dm['element']] == target['element']:
        return "Eating God" if same_polarity else "Hurting Officer"
        
    # 3. Wealth (Day Master controls Target)
    wealth_cycle = {'Wood': 'Earth', 'Earth': 'Water', 'Water': 'Fire', 'Fire': 'Metal', 'Metal': 'Wood'}
    if wealth_cycle[dm['element']] == target['element']:
        return "Indirect Wealth" if same_polarity else "Direct Wealth"
        
    # 4. Influence/Power (Target controls Day Master)
    if wealth_cycle[target['element']] == dm['element']:
        return "Seven Killings" if same_polarity else "Direct Officer"
        
    # 5. Resource (Target produces Day Master)
    if output_cycle[target['element']] == dm['element']:
        return "Indirect Resource" if same_polarity else "Direct Resource"

    return "Unknown"

def calculate_chart_ten_gods(pillars):
    """Calculates the Ten Gods for the Heavenly Stems of the Year, Month, and Hour pillars."""
    # The Day Master is the first character (Stem) of the Day Pillar
    # Assuming pillars look like "Jia Zi", we split by space and take the first word.
    try:
        day_master = pillars['day'].split(' ')[0] 
        
        return {
            'year': get_ten_god(day_master, pillars['year'].split(' ')[0]),
            'month': get_ten_god(day_master, pillars['month'].split(' ')[0]),
            'day': 'Day Master', # The Day Master is self
            'hour': get_ten_god(day_master, pillars['hour'].split(' ')[0])
        }
    except:
        return {'year': 'N/A', 'month': 'N/A', 'day': 'Day Master', 'hour': 'N/A'}