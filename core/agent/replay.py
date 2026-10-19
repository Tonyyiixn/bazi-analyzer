"""Record/replay harness for BaziAgent.

The agent talks to the outside world in exactly two places: the Claude
Messages API (self._client.messages.create) and the MCP tool server
(self._call_tool). Recording wraps both and logs every exchange, in order, to
a JSON file. Replay swaps both for stubs that serve the logged responses back,
so a recorded conversation re-runs offline, deterministically and for free -
everything in between (prompt assembly, the tool loop, fact merging, the
consistency gate, guardrails) is the real code.

Each stub also checks that the request it is asked to answer is the one that
was recorded. If the code under test now sends something different (an edited
prompt, a different tool argument, an extra loop iteration), replay raises
ReplayDivergence with a diff of the first difference, instead of quietly
serving a response to a question that was never asked. Lenient mode
(strict=False) logs request mismatches and keeps going, which is useful after
a deliberate prompt change; a change in the *sequence* of calls is always
fatal, since there is no recorded response to serve.

Recording file layout:
    {
      "format_version": 1,
      "metadata": {"recorded_at", "today", "model", "sdk_version"},
      "input":    {"messages": [...], "skill_id": ...},   # args to BaziAgent.run
      "tools":    [...],                                  # MCP tool list at start()
      "events":   [{"type": "model_call", "request": {...}, "response": {...}},
                   {"type": "tool_call", "name": ..., "input": {...}, "output": "..."},
                   ...],
      "result":   {...}                                   # what run() returned
    }
"""
import json
import logging
from datetime import date, datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import anthropic
from anthropic.types import Message
from pydantic import BaseModel

from core.agent.orchestrator import MODEL, BaziAgent

logger = logging.getLogger(__name__)

FORMAT_VERSION = 1
MAX_DIFFS = 10
SNIPPET_CHARS = 120
_MISSING = object()


class ReplayDivergence(Exception):
    """The code under replay asked for something the recording can't answer."""


def to_jsonable(obj):
    """SDK objects (the assistant content blocks the loop appends to the
    conversation) to plain JSON. Recording and replay both serialize requests
    through this, so a replayed request compares equal to its recording."""
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json")
    if isinstance(obj, dict):
        return {k: to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(v) for v in obj]
    return obj


def _differences(recorded, actual, path="$"):
    """Yields (path, recorded, actual) for each leaf where the two differ."""
    if type(recorded) is not type(actual):
        yield path, recorded, actual
    elif isinstance(recorded, dict):
        for key in sorted(recorded.keys() | actual.keys()):
            yield from _differences(recorded.get(key, _MISSING), actual.get(key, _MISSING), f"{path}.{key}")
    elif isinstance(recorded, list):
        for i in range(max(len(recorded), len(actual))):
            yield from _differences(
                recorded[i] if i < len(recorded) else _MISSING,
                actual[i] if i < len(actual) else _MISSING,
                f"{path}[{i}]",
            )
    elif recorded != actual:
        yield path, recorded, actual


def _show(value, start: int = 0) -> str:
    if value is _MISSING:
        return "<missing>"
    if isinstance(value, str):
        snippet = value[start:start + SNIPPET_CHARS]
        prefix = "..." if start else ""
        suffix = "..." if start + SNIPPET_CHARS < len(value) else ""
        return prefix + json.dumps(snippet, ensure_ascii=False) + suffix
    text = json.dumps(value, ensure_ascii=False)
    return text if len(text) <= SNIPPET_CHARS else text[:SNIPPET_CHARS] + "..."


def json_diff(recorded, actual) -> str:
    """One entry per differing JSON path. Prompts are single long strings, so
    a string difference shows only the text around the first changed
    character rather than the whole value twice."""
    diffs = list(_differences(recorded, actual))
    out = []
    for path, old, new in diffs[:MAX_DIFFS]:
        start = 0
        if isinstance(old, str) and isinstance(new, str):
            first = next((i for i, (a, b) in enumerate(zip(old, new)) if a != b), min(len(old), len(new)))
            start = max(0, first - SNIPPET_CHARS // 3)
            path = f"{path} (char {first})"
        out.append(f"  at {path}:\n    recorded: {_show(old, start)}\n    replayed: {_show(new, start)}")
    if len(diffs) > MAX_DIFFS:
        out.append(f"  ... and {len(diffs) - MAX_DIFFS} more differences")
    return "\n".join(out)


def load_recording(path: str | Path) -> dict:
    recording = json.loads(Path(path).read_text(encoding="utf-8"))
    version = recording.get("format_version")
    if version != FORMAT_VERSION:
        raise ValueError(f"{path}: recording format_version {version}, expected {FORMAT_VERSION}")
    return recording


def save_recording(recording: dict, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(recording, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


# --- Recording -------------------------------------------------------------

class RecordingAgent(BaziAgent):
    """The real agent (real API, real MCP subprocess), with every model and
    tool call appended to self.events as it happens."""

    def __init__(self, client=None):
        super().__init__(client=client)
        self.events: list[dict] = []
        self.today: date | None = None
        self._real_client = self._client
        self._client = SimpleNamespace(messages=SimpleNamespace(create=self._record_model_call))

    def _today(self) -> date:
        self.today = super()._today()
        return self.today

    async def _record_model_call(self, **kwargs):
        # Serialize the request before the call: the loop mutates its
        # conversation list afterwards, and we want what was actually sent.
        request = to_jsonable(kwargs)
        response = await self._real_client.messages.create(**kwargs)
        self.events.append({"type": "model_call", "request": request, "response": to_jsonable(response)})
        return response

    async def _call_tool(self, name: str, arguments: dict) -> str:
        output = await super()._call_tool(name, arguments)
        self.events.append({"type": "tool_call", "name": name, "input": to_jsonable(arguments), "output": output})
        return output


async def record(messages: list[dict], skill_id: str | None, client=None) -> dict:
    """Runs one real BaziAgent.run() and returns it as a recording dict.
    client defaults to the real API; tests pass a scripted stand-in."""
    agent = RecordingAgent(client=client)
    await agent.start()
    try:
        result = await agent.run(messages, skill_id)
    finally:
        await agent.stop()

    return {
        "format_version": FORMAT_VERSION,
        "metadata": {
            "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "today": agent.today.isoformat(),
            "model": MODEL,
            "sdk_version": anthropic.__version__,
        },
        "input": {"messages": to_jsonable(messages), "skill_id": skill_id},
        "tools": agent._tools,
        "events": agent.events,
        "result": result,
    }


# --- Replay ----------------------------------------------------------------

class ReplayAgent(BaziAgent):
    """The real agent loop with both external boundaries stubbed from a
    recording: no API key, no network, no MCP subprocess."""

    def __init__(self, recording: dict, strict: bool = True):
        self._recording = recording
        self._events = recording["events"]
        self._cursor = 0
        self.strict = strict
        self.divergences: list[str] = []
        super().__init__(client=SimpleNamespace(messages=SimpleNamespace(create=self._replay_model_call)))

    async def start(self):
        self._tools = self._recording["tools"]

    def _today(self) -> date:
        return date.fromisoformat(self._recording["metadata"]["today"])

    def _next_event(self, kind: str) -> tuple[int, dict]:
        index = self._cursor
        if index >= len(self._events):
            raise ReplayDivergence(
                f"event #{index}: agent made a {kind} after the recording ended "
                f"({len(self._events)} events recorded)"
            )
        event = self._events[index]
        if event["type"] != kind:
            raise ReplayDivergence(f"event #{index}: agent made a {kind}, recording has a {event['type']}")
        self._cursor += 1
        return index, event

    def _check(self, label: str, recorded, actual) -> None:
        if recorded == actual:
            return
        message = f"{label} differs from the recording:\n{json_diff(recorded, actual)}"
        if self.strict:
            raise ReplayDivergence(message)
        logger.warning(message)
        self.divergences.append(message)

    async def _replay_model_call(self, **kwargs) -> Message:
        index, event = self._next_event("model_call")
        self._check(f"event #{index} (model_call) request", event["request"], to_jsonable(kwargs))
        return Message.model_validate(event["response"])

    async def _call_tool(self, name: str, arguments: dict) -> str:
        index, event = self._next_event("tool_call")
        self._check(
            f"event #{index} (tool_call) input",
            {"name": event["name"], "input": event["input"]},
            {"name": name, "input": to_jsonable(arguments)},
        )
        return event["output"]

    def check_exhausted(self) -> None:
        unused = len(self._events) - self._cursor
        if unused:
            raise ReplayDivergence(
                f"agent finished after {self._cursor} events but the recording has {unused} more - "
                f"next unused is a {self._events[self._cursor]['type']}"
            )


async def replay(recording: dict, strict: bool = True) -> dict:
    """Re-runs a recording through the stubbed agent. Raises ReplayDivergence
    (strict) or returns every mismatch in "divergences" (lenient)."""
    agent = ReplayAgent(recording, strict=strict)
    await agent.start()
    result = await agent.run(recording["input"]["messages"], recording["input"]["skill_id"])
    agent.check_exhausted()
    agent._check("final result", recording["result"], result)
    return {"result": result, "divergences": agent.divergences}
