"""MCP server exposing the Bazi calculation engines as tools.

Wraps the pure functions in core/time_engine.py and core/bazi_math.py so any
MCP client (including our own agent orchestrator) can call them by name
instead of the backend pre-computing everything itself.
"""
from mcp.server.fastmcp import FastMCP

from core.time_engine import get_true_solar_time
from core.bazi_math import calculate_bazi_chart, get_element_counts, calculate_chart_ten_gods
from core.bazi_interactions import find_branch_interactions, find_stem_combinations, analyze_liu_nian
from core.bazi_strength import analyze_day_master_strength
from core.rag import get_index

mcp = FastMCP("bazi-engine")


@mcp.tool()
def calculate_full_chart(year: int, month: int, day: int, hour: int, minute: int, gender: str, city: str) -> dict:
    """Compute a complete Bazi natal chart for a birth date/time/city.

    Chains true-solar-time correction, the Four Pillars calculation, the Da Yun
    (10-year luck pillar) cycles, the Five Elements distribution, the Ten
    Gods (Shishen) for each pillar's stem AND branch (via the branch's dominant
    hidden stem) relative to the Day Master, every active branch interaction
    (clashes/combinations/three-harmonies/punishments/harms/breaks) between
    the four natal branches, every adjacent-pillar Heavenly Stem combination
    (天干五合), and Day Master strength (身強/身弱) with favorable/unfavorable
    elements via the 扶抑 method. Use this for any question about a specific
    person's chart - it's the fastest way to get everything needed for a
    reading in one call.

    gender must be "Male" or "Female" (affects the Da Yun sequence direction).
    """
    adj_year, adj_month, adj_day, adj_hour, adj_minute = get_true_solar_time(
        year, month, day, hour, minute, city
    )
    pillars, da_yuns = calculate_bazi_chart(adj_year, adj_month, adj_day, adj_hour, adj_minute, gender)
    elements = get_element_counts(pillars)
    ten_gods = calculate_chart_ten_gods(pillars)
    branch_interactions = find_branch_interactions(pillars)
    stem_combinations = find_stem_combinations(pillars)
    day_master_strength = analyze_day_master_strength(pillars)

    return {
        "pillars": pillars,
        "da_yuns": da_yuns,
        "elements": elements,
        "ten_gods": ten_gods,
        "branch_interactions": branch_interactions,
        "stem_combinations": stem_combinations,
        "day_master_strength": day_master_strength,
        "true_solar_time": {
            "year": adj_year, "month": adj_month, "day": adj_day,
            "hour": adj_hour, "minute": adj_minute,
        },
    }


@mcp.tool()
def get_element_balance(pillars: dict) -> dict:
    """Count the Five Elements (Wood/Fire/Earth/Metal/Water) across a chart's
    8 characters. `pillars` must have "year"/"month"/"day"/"hour" keys, each a
    2-character stem+branch string, as returned by calculate_full_chart."""
    return get_element_counts(pillars)


@mcp.tool()
def get_ten_gods(pillars: dict) -> dict:
    """Compute the Ten Gods (Shishen) relationship of each pillar's stem AND
    branch (via the branch's dominant hidden stem) to the Day Master.
    `pillars` must have "year"/"month"/"day"/"hour" keys, each a 2-character
    stem+branch string, as returned by calculate_full_chart. Returns, per
    pillar, {"stem": <Ten God>, "branch": <Ten God>}."""
    return calculate_chart_ten_gods(pillars)


@mcp.tool()
def get_branch_interactions(pillars: dict) -> dict:
    """Detect every active Earthly Branch interaction between a chart's
    Year/Month/Day/Hour branches - clashes (沖), combinations (合),
    three-harmonies (三合, full or partial), punishments (刑), harms (害),
    and breaks (破). `pillars` must have "year"/"month"/"day"/"hour" keys,
    each a 2-character stem+branch string, as returned by
    calculate_full_chart.

    This is deterministic rule-detection, not judgment - use it instead of
    inspecting the branches yourself, since spotting these interactions by
    eye is exactly the kind of structural lookup that's easy to get wrong.
    Each result includes which pillar(s) are involved (e.g. "day"+"hour")
    so you can say precisely which parts of the chart are affected, plus
    the resulting element for combinations/three-harmonies. An empty list
    means no interactions are active in this chart - don't invent any."""
    return {"interactions": find_branch_interactions(pillars)}


@mcp.tool()
def get_stem_combinations(pillars: dict) -> dict:
    """Detect Heavenly Stem combinations (天干五合) between ADJACENT
    pillars' stems (Year-Month, Month-Day, Day-Hour) - non-adjacent stem
    pairs are deliberately not flagged, since that combination effect is
    much weaker in practice. `pillars` must have "year"/"month"/"day"/"hour"
    keys, each a 2-character stem+branch string, as returned by
    calculate_full_chart.

    Each result flags "involves_day_master" (traditionally the most
    significant case - the self being pulled toward/tied to whatever the
    other stem represents) and a "season_supports_transformation" heuristic
    (whether the Month branch's element matches or generates the resulting
    element - one of several traditional conditions for true transformation
    合化 vs. a structural-only combination 合而不化; it does not check
    whether the resulting element is opposed elsewhere in the chart, so
    treat it as a signal to weigh, not a final verdict). An empty list means
    no adjacent stem combinations are present - don't invent any."""
    return {"combinations": find_stem_combinations(pillars)}


@mcp.tool()
def get_liu_nian(pillars: dict, year: int) -> dict:
    """Compute the Liu Nian (流年, annual pillar) for a given year and how it
    interacts with a natal chart - use this for any "this year"/"next
    year"/specific-year question. `pillars` must have "year"/"month"/"day"/
    "hour" keys, each a 2-character stem+branch string, as returned by
    calculate_full_chart. `year` is a plain calendar year (e.g. 2026) - check
    your instructions for today's date rather than guessing what year it is.

    Returns:
    - "pillar": the year's GanZhi, e.g. "丙午"
    - "ten_gods": {"stem", "branch"} relationship to the Day Master
    - "branch_interactions": every clash/combination/three-harmony/
      punishment/harm/break the year's branch forms against the natal
      branches (same detection as get_branch_interactions)
    - "stem_combination_with_day_master": non-null only if the year's stem
      pairs with the Day Master specifically (the traditionally significant
      case per stem_combinations.md) - null otherwise, not "no combination
      exists at all" for other stems, since only the Day Master pairing is
      checked here."""
    return analyze_liu_nian(pillars, year)


@mcp.tool()
def get_day_master_strength(pillars: dict) -> dict:
    """Score Day Master strength (身強/身弱) and derive favorable/unfavorable
    elements using the 扶抑 (Support/Suppress) method. `pillars` must have
    "year"/"month"/"day"/"hour" keys, each a 2-character stem+branch string,
    as returned by calculate_full_chart.

    IMPORTANT CAVEAT: 扶抑 is one of several traditional methods for
    selecting favorable elements (others: 調候/通關/病藥) and can disagree
    with them on the same chart - this app implements 扶抑 only, as a
    documented default, not an uncontested truth. Present "favorable_
    elements"/"unfavorable_elements" as this method's read, not an absolute
    fact.

    Returns "strength" ("strong"/"weak"/"balanced"), "support_weight" vs
    "drain_weight", a "factors" breakdown (every non-Day-Master character's
    Ten God, category, and weight - use this to explain WHY the verdict
    came out this way, e.g. "your Month branch selfishly weighs double"),
    and the resulting favorable/unfavorable elements. When "strength" is
    "balanced", both element lists are empty and "note" explains why - do
    not force a favorable-element claim in that case."""
    return analyze_day_master_strength(pillars)


@mcp.tool()
def search_bazi_principles(query: str) -> dict:
    """Search a small curated library of traditional Bazi interpretive
    principles (Day Master strength, Five Elements cycles, Ten Gods,
    branch clashes/combinations, Da Yun timing) for passages relevant to
    the query. Use this before making interpretive claims (e.g. what a
    Ten God or element imbalance "means") so the reading is grounded in
    this reference material rather than invented from general knowledge.

    NOTE: this library is a draft starter set pending human expert review -
    treat it as a helpful reference, not infallible scripture, and don't
    overstate certainty beyond what the passage itself says.

    Returns up to 3 relevant principle documents, each with a topic slug
    and its full markdown content. Returns an empty list if nothing in the
    library is relevant to the query - in that case, answer from general
    Bazi knowledge instead."""
    return {"results": get_index().search(query, k=3)}


if __name__ == "__main__":
    mcp.run()
