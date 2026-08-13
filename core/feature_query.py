"""Builds a keyword query for principle retrieval directly from a chart's
already-computed features, instead of depending on the agent to word a
free-text search well. Ten God names, strength labels, and interaction
types are exact vocabulary used in the principles library, so feeding
them in verbatim retrieves more reliably against the TF-IDF index than
a paraphrased question does.
"""

INTERACTION_QUERY_TERMS = {
    "clash": "clash chong",
    "combination": "combination he",
    "three_harmony": "three harmony sanhe",
    "punishment": "punishment xing",
    "harm": "harm hai",
    "break": "break po",
}


def build_principle_query(
    ten_gods: dict, branch_interactions: list, stem_combinations: list, day_master_strength: dict
) -> str:
    terms = [f"Day Master {day_master_strength['strength']} strength {day_master_strength['method']}"]

    for el in day_master_strength.get("favorable_elements", []):
        terms.append(f"favorable {el}")
    for el in day_master_strength.get("unfavorable_elements", []):
        terms.append(f"unfavorable {el}")

    for pillar in ten_gods.values():
        for god in (pillar.get("stem"), pillar.get("branch")):
            if god and god not in ("Day Master", "N/A", "Unknown"):
                terms.append(god)

    for it in branch_interactions:
        terms.append(INTERACTION_QUERY_TERMS.get(it["type"], it["type"]))
        if it.get("element"):
            terms.append(it["element"])

    for c in stem_combinations:
        terms.append(f"stem combination {c['element']}")
        if c.get("involves_day_master"):
            terms.append("Day Master combination")

    return " ".join(terms)
