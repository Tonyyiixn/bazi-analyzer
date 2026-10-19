"""Tests for core/agent/replay.py - the record/replay harness.

The recording is made by RecordingAgent against the real MCP tool server
(a subprocess, as in production), with a scripted stand-in for the Claude API
so no key or network is needed. Every replay test then re-runs that recording
with both boundaries stubbed. get_day_master_strength is the scripted tool
because calculate_full_chart geocodes the birth city over the network.
"""
import asyncio
import copy
import json
from types import SimpleNamespace

import pytest
from anthropic.types import Message

from core.agent import orchestrator
from core.agent.replay import ReplayDivergence, load_recording, record, replay, save_recording

PILLARS = {"year": "庚午", "month": "辛巳", "day": "庚辰", "hour": "甲申"}
USER_MESSAGES = [{"role": "user", "content": "My pillars are 庚午 辛巳 庚辰 甲申. Is my Day Master strong?"}]


def _message(content: list[dict], stop_reason: str) -> Message:
    return Message.model_validate({
        "id": "msg_scripted",
        "type": "message",
        "role": "assistant",
        "model": orchestrator.MODEL,
        "content": content,
        "stop_reason": stop_reason,
        "stop_sequence": None,
        "usage": {"input_tokens": 0, "output_tokens": 0},
    })


class ScriptedClient:
    """Plays the Claude API: one tool call, then a final answer."""

    def __init__(self):
        self._responses = [
            _message(
                [
                    {"type": "text", "text": "Let me score your Day Master."},
                    {"type": "tool_use", "id": "toolu_01", "name": "get_day_master_strength",
                     "input": {"pillars": PILLARS}},
                ],
                "tool_use",
            ),
            _message([{"type": "text", "text": "Using the Support/Suppress method, your Day Master is strong."}],
                     "end_turn"),
        ]
        self.messages = SimpleNamespace(create=self._create)

    async def _create(self, **kwargs):
        return self._responses.pop(0)


@pytest.fixture(scope="module")
def recording_file(tmp_path_factory):
    recording = asyncio.run(record(USER_MESSAGES, "general", client=ScriptedClient()))
    path = tmp_path_factory.mktemp("recordings") / "scripted.json"
    save_recording(recording, path)
    return path


@pytest.fixture
def recording(recording_file):
    """A fresh copy per test, loaded back from disk like the CLI does, so
    tests can tamper with it freely."""
    return copy.deepcopy(load_recording(recording_file))


def test_recording_captures_both_boundaries_in_order(recording):
    assert [e["type"] for e in recording["events"]] == ["model_call", "tool_call", "model_call"]

    tool_call = recording["events"][1]
    assert tool_call["name"] == "get_day_master_strength"
    assert tool_call["input"] == {"pillars": PILLARS}
    assert json.loads(tool_call["output"])["strength"] in ("strong", "weak", "balanced")

    # The second request carries the assistant tool_use turn and its result.
    second_request = recording["events"][2]["request"]
    assert second_request["messages"][-1]["content"][0]["tool_use_id"] == "toolu_01"
    assert recording["tools"], "MCP tool list should be captured at start()"


def test_replay_reproduces_recorded_result(recording):
    outcome = asyncio.run(replay(recording))
    assert outcome["divergences"] == []
    assert outcome["result"] == recording["result"]


def test_replay_recomputes_result_rather_than_copying_it(recording):
    # The consistency gate and guardrails run for real during replay, so a
    # result that no longer matches what the code computes is caught.
    recording["result"]["consistency_warnings"] = ["a warning the code never produced"]
    with pytest.raises(ReplayDivergence, match="final result"):
        asyncio.run(replay(recording))


def test_replay_detects_changed_system_prompt(recording, monkeypatch):
    monkeypatch.setattr(orchestrator, "BASE_PERSONA", orchestrator.BASE_PERSONA + " Be brief.")
    with pytest.raises(ReplayDivergence, match=r"event #0 \(model_call\) request") as exc:
        asyncio.run(replay(recording))
    assert "Be brief." in str(exc.value)


def test_replay_detects_changed_tool_input(recording):
    # The recorded model response now asks for different pillars, so the
    # agent's tool call no longer matches the recorded one.
    tool_use = recording["events"][0]["response"]["content"][1]
    tool_use["input"]["pillars"]["hour"] = "乙酉"
    with pytest.raises(ReplayDivergence, match=r"event #1 \(tool_call\) input"):
        asyncio.run(replay(recording))


def test_replay_detects_extra_call_past_end_of_recording(recording):
    recording["events"] = recording["events"][:2]
    with pytest.raises(ReplayDivergence, match="after the recording ended"):
        asyncio.run(replay(recording))


def test_replay_detects_unused_recorded_events(recording):
    recording["events"].append(copy.deepcopy(recording["events"][1]))
    with pytest.raises(ReplayDivergence, match="1 more"):
        asyncio.run(replay(recording))


def test_lenient_replay_collects_every_request_mismatch(recording, monkeypatch):
    monkeypatch.setattr(orchestrator, "BASE_PERSONA", orchestrator.BASE_PERSONA + " Be brief.")
    outcome = asyncio.run(replay(recording, strict=False))
    assert len(outcome["divergences"]) == 2  # both model calls carry the system prompt
    assert outcome["result"] == recording["result"]
