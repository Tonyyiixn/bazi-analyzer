"""Cheap, rule-based post-generation check that flags reply text which
contradicts the canonical chart facts the agent itself computed via tool
calls during the same turn. Pure keyword/regex matching over the reply
text - no extra LLM call - so it's fast enough to run on every response.

This flags likely contradictions for logging/surfacing; it does not
silently rewrite, block, or "fix" the reply. False positives are possible
(natural language is messy) - treat warnings as a signal to look closer,
not proof the model hallucinated.

Known limitation: `facts` reflects only the LAST tool call of each kind in
a turn. If a reply legitimately discusses a Liu Nian year's own branch
interactions (a separate concept from the natal chart's), this gate has
no way to distinguish that from an invented natal interaction, since it
only tracks the natal calculate_full_chart/get_branch_interactions facts.
"""
import re

ELEMENTS = ["Wood", "Fire", "Earth", "Metal", "Water"]

STRENGTH_PHRASES = {
    "strong": ["day master is strong", "day master reads as strong", "strong day master"],
    "weak": ["day master is weak", "day master reads as weak", "weak day master"],
    "balanced": ["day master is balanced", "day master reads as balanced", "balanced day master"],
}

INTERACTION_KEYWORDS = ["clash", "combination", "three harmony", "punishment", "harm", "break"]


def _elements_near(text_lower: str, keyword: str, window: int = 40) -> set[str]:
    hits = set()
    for m in re.finditer(re.escape(keyword), text_lower):
        start, end = max(0, m.start() - window), min(len(text_lower), m.end() + window)
        snippet = text_lower[start:end]
        for el in ELEMENTS:
            if re.search(rf"\b{el.lower()}\b", snippet):
                hits.add(el)
    return hits


def check_consistency(reply: str, facts: dict) -> list[str]:
    warnings = []
    lower = reply.lower()

    strength = facts.get("day_master_strength")
    if strength:
        actual = strength.get("strength")
        for claimed, phrases in STRENGTH_PHRASES.items():
            if claimed != actual and any(p in lower for p in phrases):
                warnings.append(
                    f"Reply claims Day Master strength is '{claimed}' but the computed strength is '{actual}'."
                )

        favorable = set(strength.get("favorable_elements") or [])
        unfavorable = set(strength.get("unfavorable_elements") or [])
        for el in _elements_near(lower, "favorable") & unfavorable:
            warnings.append(
                f"Reply mentions {el} near 'favorable' but computed unfavorable_elements includes {el}."
            )
        for el in _elements_near(lower, "unfavorable") & favorable:
            warnings.append(
                f"Reply mentions {el} near 'unfavorable' but computed favorable_elements includes {el}."
            )

    branch_interactions = facts.get("branch_interactions")
    if branch_interactions is not None and len(branch_interactions) == 0:
        for kw in INTERACTION_KEYWORDS:
            if re.search(rf"\b{kw}\b", lower):
                warnings.append(
                    f"Reply mentions '{kw}' but no branch interactions were detected in this natal chart."
                )
                break

    stem_combinations = facts.get("stem_combinations")
    if stem_combinations is not None and len(stem_combinations) == 0:
        if "stem combination" in lower or "combine with" in lower:
            warnings.append(
                "Reply mentions a stem combination but none were detected between this chart's adjacent pillars."
            )

    return warnings
