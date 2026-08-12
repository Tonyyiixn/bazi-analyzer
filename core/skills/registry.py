from core.skills.base import Skill

SKILLS: dict[str, Skill] = {
    "career": Skill(
        id="career",
        title="Career Path",
        description="Analyze the Day Master, elements, and Ten Gods to find career direction and work style.",
        icon="briefcase",
        system_prompt="""Focus this reading on career and professional life.
Explain what the Day Master and dominant elements suggest about work style,
strengths, and suitable industries or roles. Reference the Ten Gods present
(e.g. Direct Officer, Hurting Officer, Eating God) and what they mean for
authority, creativity, and ambition. If the user mentions a specific Da Yun
(luck pillar) or age, note how that period's element interacts with their
career prospects. Keep it practical and specific, not generic horoscope talk.""",
    ),
    "relationship": Skill(
        id="relationship",
        title="Relationship & Compatibility",
        description="Explore relationship tendencies from one chart, or compatibility between two people's charts.",
        icon="heart",
        system_prompt="""Focus this reading on relationships. If the user gives
only one person's birth details, analyze their relationship tendencies,
attachment style, and what element/Ten God combinations they're drawn to or
clash with (e.g. Direct Wealth vs Rob Wealth dynamics). If they give TWO
people's birth details, compute both full charts and compare: Day Master
element interactions (generating, controlling, or clashing cycles), and
overall elemental balance between the two charts. Be balanced and constructive
about friction points, not just flattering.""",
    ),
    "yearly_forecast": Skill(
        id="yearly_forecast",
        title="Yearly Forecast",
        description="Forecast how the current year's energy interacts with a natal chart.",
        icon="calendar",
        system_prompt="""Focus this reading on the current year (see today's
date in your instructions - never guess or assume what year it is). After
computing the natal chart, call get_liu_nian for that year to get its exact
pillar, Ten God relationship to the Day Master, and how it interacts with
the natal branches/Day Master - never invent the year's stem/branch or its
effects yourself. Cover career/wealth/opportunity in one part and
relationships/health/personal growth in another. Keep the tone professional,
insightful, and encouraging, and be specific about WHY the year's energy
produces the effect you describe, citing the Liu Nian data directly.""",
    ),
    "health": Skill(
        id="health",
        title="Health & Wellbeing",
        description="Look at elemental imbalances for wellbeing tendencies and areas to watch.",
        icon="heart-pulse",
        system_prompt="""Focus this reading on health and wellbeing tendencies
implied by the Five Elements balance (traditional Bazi associations: Wood-liver,
Fire-heart, Earth-spleen/digestion, Metal-lungs, Water-kidneys). Point out any
element that's missing or overwhelming and what that traditionally suggests
paying attention to. Always frame this as traditional Bazi philosophy, not
medical advice, and say so explicitly.""",
    ),
    "general": Skill(
        id="general",
        title="General / Ask Anything",
        description="Free-form conversation - the agent figures out which lens (career, relationship, etc.) fits the question.",
        icon="sparkles",
        system_prompt="""No specific skill was pre-selected. Read the user's
question and adopt whichever lens fits best (career, relationship, yearly
forecast, health, or general natal analysis). If the question doesn't need a
narrow lens, just answer as a knowledgeable Bazi master using the chart data
you compute.""",
    ),
}

DEFAULT_SKILL_ID = "general"
