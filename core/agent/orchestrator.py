"""Claude-driven agent loop that calls the Bazi engines over MCP.

One BaziAgent instance is created at FastAPI startup, keeps a live MCP
ClientSession open against core/mcp_server.py for the lifetime of the app,
and runs the Claude tool-use loop against it per chat request.
"""
import json
import logging
import os
import sys
from contextlib import AsyncExitStack
from datetime import date
from pathlib import Path

import anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from core.consistency_gate import check_consistency
from core.skills.registry import SKILLS, DEFAULT_SKILL_ID

logger = logging.getLogger(__name__)

MODEL = "claude-haiku-4-5"
MAX_TOOL_ITERATIONS = 6
MAX_TOKENS = 4096
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

BASE_PERSONA = """You are an expert Bazi (Four Pillars of Destiny) master \
embedded in an app called Bazi AI. You have tools to compute a person's exact \
natal chart (pillars, Da Yun luck cycles, Five Elements balance, Ten Gods, \
branch interactions, stem combinations, and Day Master strength) - always \
call a tool to get real chart data before making claims about someone's \
chart; never invent stems, branches, element counts, clashes/combinations, \
stem combinations, or strength/favorable-element verdicts. calculate_full_chart \
already includes a "branch_interactions" list (clashes, combinations, \
three-harmonies, punishments, harms, breaks) between the natal Year/Month/ \
Day/Hour branches, a "stem_combinations" list (天干五合) between adjacent \
pillars' stems, and a "day_master_strength" object (strong/weak/balanced, \
with a per-character "factors" breakdown and favorable/unfavorable elements) \
- read those fields rather than eyeballing the chart or reasoning about \
strength yourself; an empty interactions list means none are active, not \
that you should look harder. If the user hasn't given you a full birth \
date, time, and city yet, ask for what's missing before guessing.

IMPORTANT: day_master_strength uses ONE specific method (扶抑, Support/ \
Suppress) - say so when you state a strength verdict or favorable element \
(e.g. "using the Support/Suppress method, your Day Master reads as..."), \
since other traditional methods (調候/通關/病藥) can disagree on the same \
chart. When strength is "balanced", the tool deliberately returns no \
favorable/unfavorable elements - don't invent a skew where the method found \
none; say the chart is balanced by this method instead.

For "this year" / "next year" / any specific-year question, call get_liu_nian \
with the natal pillars and the target year (use the date given in your \
instructions below to know what year "this year" actually is - never guess \
or rely on your training data for the current year). It returns that year's \
exact pillar, Ten God relationship to the Day Master, how its branch \
interacts with the natal branches, and whether its stem combines with the \
Day Master - never invent a year's stem/branch or its effects yourself.

You also have two tools over a small curated library of traditional \
interpretive principles. Once you have a chart's pillars, prefer \
search_principles_for_chart(pillars) - it builds its search query from the \
chart's actual computed Ten Gods, strength, and interactions, so it can't \
miss a doc due to wording mismatch the way a free-text query can. Use \
search_bazi_principles(query) instead for questions not tied to a specific \
chart's features (e.g. general Da Yun timing theory). Call one of them before \
making interpretive claims (what a Ten God, element imbalance, clash, or Da \
Yun period "means") so your reading is grounded in that reference material \
rather than invented from general knowledge. That library is a draft starter \
set pending human expert review - use it as a helpful reference, not \
infallible scripture."""


def _skill_menu() -> str:
    lines = [
        f'- "{s.id}": {s.title} - {s.description}'
        for s in SKILLS.values()
        if s.id != DEFAULT_SKILL_ID
    ]
    return "\n".join(lines)


class BaziAgent:
    def __init__(self):
        self._stack = AsyncExitStack()
        self._session: ClientSession | None = None
        self._tools: list[dict] = []
        self._client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    async def start(self):
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "core.mcp_server"],
            cwd=str(PROJECT_ROOT),
        )
        read, write = await self._stack.enter_async_context(stdio_client(params))
        self._session = await self._stack.enter_async_context(ClientSession(read, write))
        await self._session.initialize()

        listed = await self._session.list_tools()
        self._tools = [
            {"name": t.name, "description": t.description or "", "input_schema": t.inputSchema}
            for t in listed.tools
        ]

    async def stop(self):
        await self._stack.aclose()

    async def _call_tool(self, name: str, arguments: dict) -> str:
        result = await self._session.call_tool(name, arguments)
        parts = [block.text for block in result.content if hasattr(block, "text")]
        return "\n".join(parts) if parts else json.dumps(result.model_dump(mode="json"))

    @staticmethod
    def _merge_tool_facts(name: str, result_text: str, facts: dict) -> None:
        """Tracks the latest natal-chart facts seen this turn, for the
        consistency gate to check the final reply against. Last call of
        each kind wins - fine since a chart's own facts don't change
        mid-conversation."""
        try:
            parsed = json.loads(result_text)
        except (json.JSONDecodeError, TypeError):
            return
        if not isinstance(parsed, dict):
            return

        if name == "calculate_full_chart":
            facts["day_master_strength"] = parsed.get("day_master_strength", facts.get("day_master_strength"))
            facts["branch_interactions"] = parsed.get("branch_interactions", facts.get("branch_interactions"))
            facts["stem_combinations"] = parsed.get("stem_combinations", facts.get("stem_combinations"))
        elif name == "get_day_master_strength":
            facts["day_master_strength"] = parsed
        elif name == "get_branch_interactions":
            facts["branch_interactions"] = parsed.get("interactions")
        elif name == "get_stem_combinations":
            facts["stem_combinations"] = parsed.get("combinations")

    async def run(self, messages: list[dict], skill_id: str | None) -> dict:
        skill = SKILLS.get(skill_id or DEFAULT_SKILL_ID, SKILLS[DEFAULT_SKILL_ID])
        system = BASE_PERSONA + "\n\n" + skill.system_prompt
        if skill.id == DEFAULT_SKILL_ID:
            system += "\n\nAvailable specialized lenses - adopt whichever fits the question:\n" + _skill_menu()
        # Computed fresh per request (not baked in at import time) so it never
        # goes stale if the server process stays up across a date/year change.
        # Placed last so it doesn't sit in front of the otherwise-stable
        # system prompt if prompt caching is ever added later.
        system += f"\n\nToday's date is {date.today().isoformat()}."

        convo = list(messages)
        facts: dict = {}

        for _ in range(MAX_TOOL_ITERATIONS):
            response = await self._client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=system,
                messages=convo,
                tools=self._tools,
            )

            if response.stop_reason != "tool_use":
                text = "".join(b.text for b in response.content if b.type == "text")
                if not text:
                    if response.stop_reason == "refusal":
                        text = "I can't help with that request."
                    elif response.stop_reason == "max_tokens":
                        text = "That answer ran out of room before finishing - try asking again, maybe more narrowly."
                warnings = check_consistency(text, facts)
                if warnings:
                    logger.warning("Consistency gate flagged reply: %s", warnings)
                return {"reply": text, "skill_used": skill.id, "consistency_warnings": warnings}

            convo.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                result_text = await self._call_tool(block.name, block.input)
                self._merge_tool_facts(block.name, result_text, facts)
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": result_text}
                )
            convo.append({"role": "user", "content": tool_results})

        return {
            "reply": "I wasn't able to finish that within the allotted tool calls - try narrowing your question.",
            "skill_used": skill.id,
            "consistency_warnings": [],
        }
