import os
import json
import anthropic
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

claude_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

RECTIFY_SCHEMA = {
    "type": "object",
    "properties": {
        "inferred_shishen": {"type": "string", "description": "The name of the Ten God (Shishen)"},
        "inferred_time_block": {"type": "string", "description": "e.g. \"11:00-13:00\""},
        "earthly_branch": {"type": "string", "description": "e.g. \"Wu\""},
        "ai_reasoning": {"type": "string", "description": "1-2 sentences explaining why"},
    },
    "required": ["inferred_shishen", "inferred_time_block", "earthly_branch", "ai_reasoning"],
    "additionalProperties": False,
}

def rectify_birth_hour(user_answers: str):
    """
    Analyzes MBTI-style user answers to deduce their Bazi birth hour (Shishen).
    Forces the AI to return a structured JSON response.
    """
    prompt = f"""You are an expert in traditional Bazi (Four Pillars of Destiny) and the Shishen (Ten Gods) system.
The user does not know their exact birth hour. Based on the following personality traits and situational reactions,
determine the most likely dominant Shishen in their Hour Pillar.

User Traits: {user_answers}

Calculate the corresponding 2-hour Chinese time block (e.g., Zi hour 23:00-01:00, Chou hour 01:00-03:00)."""

    response = claude_client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        output_config={"format": {"type": "json_schema", "schema": RECTIFY_SCHEMA}},
        messages=[{"role": "user", "content": prompt}],
    )

    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)