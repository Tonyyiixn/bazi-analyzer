"""Runs the benchmark questions against Claude and records raw replies.

Two arms, identical except for tool access:

- claude: Claude alone - it has to work the chart out itself.
- mcp:    Claude + this repo's MCP tools (core/mcp_server.py) over stdio.

Each (question, repeat) becomes one line in bench/results/<set>/<run>/<arm>.jsonl
with the raw reply text, the tool calls made, token usage and latency.
Parsing and grading happen in score.py, so a run never has to be repeated
just because the scoring changes. Re-running the same --run resumes: pairs
already recorded without an error are skipped.

By default the MCP server is launched in offline-geocoding mode - the same
city table generate.py built the gold from - so a flaky or rate-limited
Nominatim can't silently fall back to clock time and make a correct tool
call look wrong. --live-geocode uses the production server unchanged.

Two question sets: dev (small, for debugging - filter it however you like)
and eval (frozen, checksum-verified, and only ever run in full, so formal
numbers always cover the same questions).

Run from the repo root:
    python -m bench.runner --run try1 --limit 3                 # dev
    python -m bench.runner --set eval --run v1 --model claude-haiku-4-5
"""
import argparse
import asyncio
import json
import sys
import time
from contextlib import AsyncExitStack
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(__file__).parent / "data"
RESULTS_DIR = Path(__file__).parent / "results"

DEFAULT_MODEL = "claude-opus-5-5"
MAX_TOKENS = 16000
MAX_TOOL_ITERATIONS = 8

BASE_SYSTEM = """You are an expert Bazi (Four Pillars of Destiny) analyst. \
Birth times are given as local clock time; convert to true solar time for the \
birth location before determining the pillars, as is standard practice. Use \
English names for the Ten Gods: Friend, Rob Wealth, Eating God, Hurting \
Officer, Direct Wealth, Indirect Wealth, Direct Officer, Seven Killings, \
Direct Resource, Indirect Resource. Follow the requested answer format exactly."""

ARM_SYSTEM = {
    "claude": BASE_SYSTEM + "\n\nYou have no tools - work everything out yourself.",
    "mcp": BASE_SYSTEM + "\n\nYou have tools that compute Bazi charts deterministically. "
                         "Use them rather than calculating by hand, and base your answer on their output.",
}


# ---------------------------------------------------------------- MCP server

def serve_offline_mcp():
    """Entry point for the MCP subprocess in offline-geocoding mode: the
    production server with its geocoder answering from generate.py's city
    table. Unknown city names still go to the real geocoder, so a model
    writing "Hong Kong, China" or "香港" isn't penalized."""
    from bench.generate import CITIES
    from core import time_engine
    from core.mcp_server import mcp
    from types import SimpleNamespace

    live_geocode = time_engine.geolocator.geocode
    by_name = {name.lower(): coords for name, coords in CITIES.items()}

    def geocode(query, timeout=None):
        q = query.lower()
        for name, (lat, lng) in by_name.items():
            if name in q:
                return SimpleNamespace(latitude=lat, longitude=lng)
        return live_geocode(query, timeout=timeout)

    time_engine.geolocator.geocode = geocode
    mcp.run()


class McpTools:
    def __init__(self, live_geocode):
        self._stack = AsyncExitStack()
        self._live_geocode = live_geocode
        self.session: ClientSession | None = None
        self.tools: list[dict] = []

    async def __aenter__(self):
        args = ["-m", "core.mcp_server"] if self._live_geocode else ["-m", "bench.runner", "--serve-offline-mcp"]
        params = StdioServerParameters(command=sys.executable, args=args, cwd=str(ROOT))
        read, write = await self._stack.enter_async_context(stdio_client(params))
        self.session = await self._stack.enter_async_context(ClientSession(read, write))
        await self.session.initialize()
        listed = await self.session.list_tools()
        self.tools = [
            {"name": t.name, "description": t.description or "", "input_schema": t.inputSchema}
            for t in listed.tools
        ]
        return self

    async def __aexit__(self, *exc):
        await self._stack.aclose()

    async def call(self, name, arguments) -> tuple[str, bool]:
        try:
            result = await self.session.call_tool(name, arguments)
        except Exception as e:
            return f"Tool call failed: {e}", True
        parts = [block.text for block in result.content if hasattr(block, "text")]
        text = "\n".join(parts) if parts else json.dumps(result.model_dump(mode="json"))
        return text, bool(result.isError)


# ---------------------------------------------------------------- one question

def build_prompt(q):
    return f"{q['question']}\n\n{q['answer_format']}"


def _add_usage(total, usage):
    for key in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"):
        total[key] = total.get(key, 0) + (getattr(usage, key, None) or 0)


async def ask(client, args, arm, q, tools: McpTools | None):
    """Runs one question to completion. Returns the fields recorded per line."""
    convo = [{"role": "user", "content": build_prompt(q)}]
    request = {
        "model": args.model,
        "max_tokens": MAX_TOKENS,
        # Breakpoint on the system block caches tools + system, which is
        # identical for every question in an arm. The top-level marker caches
        # the growing conversation, so each tool-loop turn re-reads the
        # previous one (chart results included) instead of paying full price.
        # Prefixes under the model's minimum (e.g. the tool-less claude arm)
        # silently don't cache - no error, just zero cache tokens.
        "system": [{"type": "text", "text": ARM_SYSTEM[arm], "cache_control": {"type": "ephemeral"}}],
        "cache_control": {"type": "ephemeral"},
    }
    if args.effort:
        request["output_config"] = {"effort": args.effort}
    if tools:
        request["tools"] = tools.tools

    usage, tool_calls = {}, []
    for _ in range(MAX_TOOL_ITERATIONS):
        response = await client.messages.create(messages=convo, **request)
        _add_usage(usage, response.usage)

        if response.stop_reason != "tool_use":
            return {
                "response": "".join(b.text for b in response.content if b.type == "text"),
                "stop_reason": response.stop_reason,
                "tool_calls": tool_calls,
                "usage": usage,
            }

        convo.append({"role": "assistant", "content": response.content})
        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            text, is_error = await tools.call(block.name, block.input)
            tool_calls.append({"name": block.name, "input": block.input, "is_error": is_error})
            results.append({"type": "tool_result", "tool_use_id": block.id, "content": text, "is_error": is_error})
        convo.append({"role": "user", "content": results})

    return {"response": "", "stop_reason": "max_tool_iterations", "tool_calls": tool_calls, "usage": usage}


# ---------------------------------------------------------------- driver

def check_eval_frozen():
    """The formal set must be byte-identical to when it was frozen."""
    from bench.generate import file_sha256
    expected = (DATA_DIR / "eval.sha256").read_text().strip()
    if file_sha256(DATA_DIR / "eval.jsonl") != expected:
        raise SystemExit("data/eval.jsonl doesn't match data/eval.sha256 - the frozen eval set was modified.")


def load_questions(args):
    if args.set == "eval":
        check_eval_frozen()
    questions = [json.loads(line) for line in (DATA_DIR / f"{args.set}.jsonl").open(encoding="utf-8")]
    if args.suite:
        questions = [q for q in questions if q["suite"] in args.suite]
    if args.ids:
        questions = [q for q in questions if q["id"] in args.ids]
    if args.limit:
        # Per suite, so --limit 3 still exercises all three.
        seen = {}
        questions = [q for q in questions if seen.setdefault(q["suite"], []).append(q) or len(seen[q["suite"]]) <= args.limit]
    return questions


def load_done(path):
    """(id, repeat) pairs already recorded without an error."""
    if not path.exists():
        return set()
    done = set()
    for line in path.open(encoding="utf-8"):
        rec = json.loads(line)
        if not rec.get("error"):
            done.add((rec["id"], rec["repeat"]))
    return done


async def run_arm(client, args, arm, questions, out_path):
    done = load_done(out_path)
    jobs = [
        (q, r) for q in questions
        for r in range(args.repeats or q["repeats"])
        if (q["id"], r) not in done
    ]
    print(f"[{arm}] {len(jobs)} to run ({len(done)} already done) -> {out_path}")
    if not jobs:
        return

    sem = asyncio.Semaphore(args.concurrency)
    lock = asyncio.Lock()
    counts = {"ok": 0, "error": 0}

    async with AsyncExitStack() as stack:
        tools = await stack.enter_async_context(McpTools(args.live_geocode)) if arm == "mcp" else None
        out = stack.enter_context(out_path.open("a", encoding="utf-8"))

        async def one(q, repeat):
            async with sem:
                started = time.monotonic()
                rec = {"id": q["id"], "set": args.set, "suite": q["suite"], "arm": arm, "model": args.model,
                       "effort": args.effort, "repeat": repeat}
                try:
                    rec.update(await ask(client, args, arm, q, tools))
                    rec["error"] = None
                except (anthropic.AuthenticationError, anthropic.PermissionDeniedError, anthropic.NotFoundError):
                    raise  # bad key or model name: every other call would fail the same way
                except anthropic.APIStatusError as e:
                    rec["error"] = f"{type(e).__name__} {e.status_code}: {e.message}"
                except anthropic.APIConnectionError as e:
                    rec["error"] = f"{type(e).__name__}: {e}"
                rec["latency_s"] = round(time.monotonic() - started, 2)
                async with lock:
                    out.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
                    out.flush()
                    counts["error" if rec["error"] else "ok"] += 1
                    n = counts["ok"] + counts["error"]
                    if rec["error"] or n % 10 == 0 or n == len(jobs):
                        print(f"[{arm}] {n}/{len(jobs)} ({counts['error']} errors)"
                              + (f" - {q['id']}: {rec['error']}" if rec["error"] else ""))

        # One call first so the shared tools+system cache exists before the
        # parallel batch - otherwise every concurrent first call writes it.
        await one(*jobs[0])
        await asyncio.gather(*(one(q, r) for q, r in jobs[1:]))


async def dry_run(args, questions):
    """No API calls: shows what would be sent and checks the MCP server
    answers a real tool call."""
    for q in questions[:3]:
        print(f"--- {q['id']} ({q['suite']}/{q['task']})\n{build_prompt(q)}\n")
    total = sum(args.repeats or q["repeats"] for q in questions)
    print(f"{len(questions)} questions, {total} calls per arm")

    birth = next(q["birth"] for q in questions)
    async with McpTools(args.live_geocode) as tools:
        print(f"MCP tools: {[t['name'] for t in tools.tools]}")
        text, is_error = await tools.call("calculate_full_chart", birth)
        chart = json.loads(text) if not is_error else text
        print(f"calculate_full_chart({birth}) -> pillars {chart['pillars'] if not is_error else chart}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--serve-offline-mcp", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--set", choices=["dev", "eval"], default="dev",
                        help="dev for debugging; eval is the frozen formal set and only runs in full")
    parser.add_argument("--run", default="default", help="results go to bench/results/<set>/<run>/")
    parser.add_argument("--arm", choices=["claude", "mcp", "both"], default="both")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--effort", choices=["low", "medium", "high", "xhigh", "max"],
                        help="omit to use the model's default")
    parser.add_argument("--suite", nargs="+", choices=["accuracy", "stability", "interactions"])
    parser.add_argument("--ids", nargs="+")
    parser.add_argument("--limit", type=int, help="first N questions per suite")
    parser.add_argument("--repeats", type=int, help="override every question's repeat count")
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--live-geocode", action="store_true", help="use the real Nominatim geocoder in the MCP arm")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.serve_offline_mcp:
        return serve_offline_mcp()

    if args.set == "eval" and not args.dry_run and (args.suite or args.ids or args.limit or args.repeats):
        parser.error("eval only runs in full - debug with --set dev instead of filtering eval")

    load_dotenv(ROOT / ".env")
    questions = load_questions(args)
    if args.dry_run:
        return asyncio.run(dry_run(args, questions))

    run_dir = RESULTS_DIR / args.set / args.run
    run_dir.mkdir(parents=True, exist_ok=True)
    client = anthropic.AsyncAnthropic()
    arms = ["claude", "mcp"] if args.arm == "both" else [args.arm]

    async def all_arms():
        for arm in arms:
            await run_arm(client, args, arm, questions, run_dir / f"{arm}.jsonl")

    asyncio.run(all_arms())


if __name__ == "__main__":
    main()
