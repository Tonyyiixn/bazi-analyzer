from lunar_python import Solar

def get_year_pillar(year):
    """Returns the Liu Nian (流年, annual pillar) GanZhi for a given year,
    e.g. 2026 -> "丙午". This is "this year's energy" for yearly-forecast
    questions, independent of any specific birth chart.

    Anchored at June 15 of that year - safely past 立春 (~Feb 4, the actual
    year-pillar boundary) and before the next year's, so it reuses the same
    lunar_python machinery that already gets the birth-year pillar right,
    without re-deriving the 立春/cycle math by hand."""
    solar_date = Solar.fromYmdHms(year, 6, 15, 12, 0, 0)
    return solar_date.getLunar().getEightChar().getYear()

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
    '丑': {'element': 'Earth', 'polarity': 'Yin'},
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

# Each Earthly Branch's dominant/main-qi hidden stem (本氣), used to give the
# branch its own Ten God relative to the Day Master, same as the stem gets.
BRANCH_MAIN_QI = {
    '子': '癸', '丑': '己', '寅': '甲', '卯': '乙', '辰': '戊',
    '巳': '丙', '午': '丁', '未': '己', '申': '庚', '酉': '辛',
    '戌': '戊', '亥': '壬',
}

def calculate_chart_ten_gods(pillars):
    """Calculates the Ten Gods for both the stem and the branch (via its
    dominant hidden stem) of the Year, Month, Day, and Hour pillars,
    relative to the Day Master. Each pillar's entry is {"stem": ..., "branch": ...}."""
    try:
        day_master = pillars['day'][0]

        result = {}
        for key in ('year', 'month', 'day', 'hour'):
            stem, branch = pillars[key][0], pillars[key][1]
            result[key] = {
                'stem': 'Day Master' if key == 'day' else get_ten_god(day_master, stem),
                'branch': get_ten_god(day_master, BRANCH_MAIN_QI[branch]),
            }
        return result
    except Exception:
        na = {'stem': 'N/A', 'branch': 'N/A'}
        return {'year': na, 'month': na, 'day': {'stem': 'Day Master', 'branch': 'N/A'}, 'hour': na}