"""Record a real agent conversation to JSON, or replay one offline.

    # Real API + real MCP tools; needs ANTHROPIC_API_KEY (read from .env)
    python bin/agent_replay.py record "Born 1990-05-15 15:00 in Shanghai. How is my career?" \
        --skill career -o recordings/career.json

    # Stubbed API + stubbed tools; no key, no network. Exit code 1 on divergence.
    python bin/agent_replay.py replay recordings/career.json
    python bin/agent_replay.py replay recordings/career.json --lenient

    # Print a recording's call timeline without running anything
    python bin/agent_replay.py show recordings/career.json
"""
import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402

from core.agent.replay import ReplayDivergence, load_recording, record, replay, save_recording  # noqa: E402


def print_timeline(recording: dict) -> None:
    meta = recording["metadata"]
    print(f"recorded {meta['recorded_at']}  model={meta['model']}  skill={recording['input']['skill_id']}")
    for i, event in enumerate(recording["events"]):
        if event["type"] == "model_call":
            response = event["response"]
            tool_uses = [b["name"] for b in response["content"] if b["type"] == "tool_use"]
            usage = response.get("usage") or {}
            detail = f"-> {', '.join(tool_uses)}" if tool_uses else ""
            print(
                f"  #{i:<3} model_call  stop={response['stop_reason']:<9} "
                f"in={usage.get('input_tokens')} out={usage.get('output_tokens')} {detail}"
            )
        else:
            print(f"  #{i:<3} tool_call   {event['name']}  ({len(event['output'])} chars out)")
    reply = recording["result"]["reply"]
    print(f"reply: {reply[:200]}{'...' if len(reply) > 200 else ''}")


def cmd_record(args) -> int:
    load_dotenv(PROJECT_ROOT / ".env")
    messages = [{"role": "user", "content": args.message}]
    recording = asyncio.run(record(messages, args.skill))
    out = args.output or PROJECT_ROOT / "recordings" / f"{datetime.now():%Y%m%d-%H%M%S}.json"
    save_recording(recording, out)
    print_timeline(recording)
    print(f"saved {out}")
    return 0


def cmd_replay(args) -> int:
    recording = load_recording(args.recording)
    try:
        outcome = asyncio.run(replay(recording, strict=not args.lenient))
    except ReplayDivergence as e:
        print(f"DIVERGED: {e}", file=sys.stderr)
        return 1

    if outcome["divergences"]:
        for d in outcome["divergences"]:
            print(f"DIVERGED: {d}\n", file=sys.stderr)
        print(f"replay finished with {len(outcome['divergences'])} divergence(s)", file=sys.stderr)
        return 1
    print(f"OK: {len(recording['events'])} events replayed, result matches the recording")
    return 0


def cmd_show(args) -> int:
    print_timeline(load_recording(args.recording))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("record", help="run one real conversation turn and save it")
    p.add_argument("message", help="the user's message")
    p.add_argument("--skill", default=None, help="skill id (career, relationship, health, yearly_forecast, general)")
    p.add_argument("-o", "--output", type=Path, help="where to write the recording (default recordings/<timestamp>.json)")
    p.set_defaults(func=cmd_record)

    p = sub.add_parser("replay", help="re-run a recording against stubbed API and tools")
    p.add_argument("recording", type=Path)
    p.add_argument("--lenient", action="store_true", help="report request mismatches instead of stopping at the first")
    p.set_defaults(func=cmd_replay)

    p = sub.add_parser("show", help="print a recording's call timeline")
    p.add_argument("recording", type=Path)
    p.set_defaults(func=cmd_show)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
