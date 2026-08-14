"""Detects high-stakes question categories in the user's latest message and
injects category-specific instructions into the system prompt for that turn
only - cheap keyword/phrase matching, no extra LLM call, so it's fast enough
to run on every request. Also does a cheap post-generation check that the
reply actually included the expected hedging/disclaimer language, mirroring
core/consistency_gate.py's flag-don't-block philosophy (except for
self_harm, where the instruction is strong enough that a missing marker is
worth a loud log, not just a quiet one).

This is a safety net on top of the model's own judgment, not a replacement
for it - keyword matching will both over- and under-trigger on real
messages. Tune the phrase lists if you see false positives/negatives in
practice.
"""
import re

CATEGORIES: dict[str, dict] = {
    "self_harm": {
        "phrases": [
            "kill myself", "end my life", "want to die", "don't want to live",
            "suicide", "suicidal", "hurt myself", "self harm", "self-harm",
            "no reason to live",
        ],
        "instruction": (
            "The user's message contains language suggesting possible thoughts of "
            "suicide or self-harm. Set aside the Bazi reading. Respond with care: "
            "acknowledge what they said, gently encourage them to reach out to a "
            "crisis line or mental health professional right now (in the US: call "
            "or text 988, the Suicide & Crisis Lifeline), and do not attempt to "
            "answer their original question with a chart reading in this message. "
            "Do not frame anything about their chart as fatalistic or as an "
            "explanation for how they feel."
        ),
        "expected_reply_markers": ["988", "crisis", "professional", "counselor", "therapist", "helpline"],
    },
    "mortality": {
        "phrases": [
            "will i die", "when will i die", "how long will i live", "my life span",
            "my lifespan", "date of my death", "when i will die", "am i going to die",
        ],
        "instruction": (
            "The user is asking for a death/lifespan prediction. Bazi is not a "
            "medically or scientifically validated way to predict mortality. "
            "Decline to give a specific age, date, or year of death. You may "
            "discuss what traditional Bazi philosophy says about the Water "
            "element or Day Master cycles in general terms if relevant, but "
            "explicitly say you won't predict a death date and that any such "
            "concern about health or safety is worth discussing with a doctor."
        ),
        "expected_reply_markers": ["won't predict", "will not predict", "can't predict", "cannot predict", "doctor", "not able to"],
    },
    "medical_diagnosis": {
        "phrases": [
            "do i have cancer", "diagnose me", "diagnose my", "what disease do i have",
            "what illness do i have", "am i sick with", "what's wrong with my health",
            "what is wrong with my health",
        ],
        "instruction": (
            "The user is asking for something close to a medical diagnosis. "
            "You may describe traditional Bazi elemental associations (e.g. "
            "Wood-liver, Fire-heart) as cultural/philosophical context only. "
            "Explicitly say this is not a medical diagnosis and isn't a "
            "substitute for seeing a doctor, and do not name a specific disease "
            "as something the user has or is likely to get."
        ),
        "expected_reply_markers": ["not a medical diagnosis", "not a diagnosis", "doctor", "medical professional", "physician"],
    },
    "major_irreversible_decision": {
        "phrases": [
            "should i divorce", "should i quit my job", "should i invest my savings",
            "should i marry", "should i have surgery", "should i sue", "should i take out a loan",
            "should i resign", "should i break up",
        ],
        "instruction": (
            "The user is asking you to make an irreversible, high-stakes life "
            "decision for them. You can describe what the chart's elements/Ten "
            "Gods/current Da Yun traditionally suggest about timing or "
            "temperament, but explicitly say the decision itself is theirs to "
            "make (with a qualified professional - financial advisor, lawyer, "
            "counselor - as relevant), not something a chart reading should "
            "decide for them."
        ),
        "expected_reply_markers": ["your decision", "up to you", "advisor", "professional", "lawyer", "counselor"],
    },
}


def detect_categories(message: str) -> list[str]:
    lower = message.lower()
    return [name for name, cfg in CATEGORIES.items() if any(p in lower for p in cfg["phrases"])]


def build_guardrail_instructions(categories: list[str]) -> str:
    if not categories:
        return ""
    blocks = [CATEGORIES[c]["instruction"] for c in categories]
    return "\n\nIMPORTANT SAFETY INSTRUCTIONS FOR THIS MESSAGE:\n" + "\n".join(f"- {b}" for b in blocks)


def check_guardrail_compliance(reply: str, categories: list[str]) -> list[str]:
    lower = reply.lower()
    warnings = []
    for c in categories:
        markers = CATEGORIES[c]["expected_reply_markers"]
        if not any(re.search(re.escape(m), lower) for m in markers):
            warnings.append(
                f"Reply may not have followed the '{c}' safety instruction - "
                f"none of its expected markers {markers} were found."
            )
    return warnings
