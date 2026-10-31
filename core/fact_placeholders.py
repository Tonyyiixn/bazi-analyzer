"""Fills {{placeholder}} tokens in the model's reply with chart facts the
agent's tools computed this turn, so the reply's strength verdict and
favorable/unfavorable elements come from tool output rather than the
model's own wording - they can't contradict the facts because the model
never writes them.

The model is told to write e.g. "your Day Master is {{day_master_strength}}"
(see FACT_PLACEHOLDER_INSTRUCTIONS); render_fact_placeholders swaps the
tokens for values. A token naming an unknown fact, or a fact no tool
computed this turn, can't be filled - it renders as UNAVAILABLE and comes
back as a warning, never as a literal "{{...}}" shown to the user.
"""
import re

PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-z_]+)\s*\}\}")
UNAVAILABLE = "(not yet calculated)"

FACT_PLACEHOLDER_INSTRUCTIONS = """Never write a Day Master strength verdict \
or a list of favorable/unfavorable elements in your own words - write these \
placeholders instead, and the app fills them in from the tool output: \
{{day_master_strength}} (strong/weak/balanced), {{favorable_elements}}, \
{{unfavorable_elements}}. For example: "using the Support/Suppress method, \
your Day Master reads as {{day_master_strength}}, so {{favorable_elements}} \
support you." Only use a placeholder after a tool has computed that fact \
this turn, and don't use the element placeholders when the chart is \
balanced."""


def _join_elements(elements: list[str]) -> str:
    if not elements:
        return "none"
    if len(elements) == 1:
        return elements[0]
    return ", ".join(elements[:-1]) + " and " + elements[-1]


def _fact_values(facts: dict) -> dict[str, str]:
    strength = facts.get("day_master_strength")
    if not strength:
        return {}
    values = {}
    if strength.get("strength"):
        values["day_master_strength"] = strength["strength"]
    if strength.get("favorable_elements") is not None:
        values["favorable_elements"] = _join_elements(strength["favorable_elements"])
    if strength.get("unfavorable_elements") is not None:
        values["unfavorable_elements"] = _join_elements(strength["unfavorable_elements"])
    return values


def render_fact_placeholders(text: str, facts: dict) -> tuple[str, list[str]]:
    """Returns (rendered text, warnings for placeholders that couldn't be filled)."""
    values = _fact_values(facts)
    warnings = []

    def fill(match: re.Match) -> str:
        name = match.group(1)
        if name in values:
            return values[name]
        warnings.append(f"Reply used placeholder '{{{{{name}}}}}' but no tool computed that fact this turn.")
        return UNAVAILABLE

    return PLACEHOLDER_RE.sub(fill, text), warnings
