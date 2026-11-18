# Bazi Bench

Does giving Claude this app's deterministic chart engine (over MCP) actually make its Bazi answers more correct and more consistent, and does the engine itself hold up on hard edge cases?

The bench answers that with four suites, run against up to five **arms**:

| Arm | What answers |
|---|---|
| `engine` | The engine alone (`calculate_full_chart` called directly, no model). Free. Edge suite only. |
| `claude` | Claude with no tools: it has to work the chart out itself. |
| `mcp` | Claude with this repo's MCP tools (`core/mcp_server.py`), the way the app runs. |

Every arm gets the same system prompt and question; the only difference is tool access.

## Results

Run on the frozen formal sets, November 2026. Models: `claude-haiku-5-5` and `claude-opus-5-5`, both at their default effort (`medium`). Engine: after the true-solar-time fix (see [The engine fix](#the-engine-fix-found-by-this-bench)).

### Main suites (`eval`: 80 charts, 240 calls per arm)

| | Haiku 5.5 | Opus 5.5 | Haiku 5.5 + MCP | Opus 5.5 + MCP |
|---|---|---|---|---|
| **Accuracy**: day pillar | 83% | 93% | 100% | 100% |
| Accuracy: a stem's Ten God | 53% | 90% | 100% | 100% |
| Accuracy: a branch's hidden stems | 37% | 87% | 100% | 100% |
| **Accuracy: all** | **58%** | **90%** | **100%** | **100%** |
| **Stability**: same ask repeated, agrees with itself / matches gold | 63% / 37% | 100% / 67% | 100% / 100% | 100% / 100% |
| Stability: reworded ask (EN + ZH), agrees with itself / matches gold | 44% / 22% | 74% / 44% | 100% / 100% | 100% / 100% |
| Stability: chart facts match gold | 63% | 93% | 100% | 100% |
| Stability: method verdict matches the engine's 扶抑 | 30% | 46% | 100% | 100% |
| **Interactions**: F1 from birth data | 80% | 95% | 100% | 100% |
| Interactions: F1 with pillars given | 97% | 100% | 100% | 100% |
| Interactions: invented on charts that have none | 25% | 8% | 0% | 0% |
| Cost | $0.39 | $3.83 (batch) | $0.23 | $8.50 |

### Edge cases (`edge-eval`: 60 cases, gold from an independent reference)

Share of cases where the pillar the edge decides (the "focus" pillar) is right:

| | Engine | Haiku 5.5 | Opus 5.5 | Haiku 5.5 + MCP | Opus 5.5 + MCP |
|---|---|---|---|---|---|
| Solar-term boundary (節) | 100% | 70% | 100% | 100% | 100% |
| 立春 (year changes) | 100% | 40% | 60% | 100% | 100% |
| 子時 hour (23:00–01:00) | 100% | 60% | 80% | 90% | 100% |
| Time zones / DST | 100% | 60% | 90% | 90% | 100% |
| Equation of time | 100% | 70% | 100% | 100% | 100% |
| Leap month (閏月) | 100% | 70% | 100% | 100% | 100% |
| **All categories** | **100%** | **62%** | **88%** | **97%** | **100%** |
| All four pillars right | 100% | 50% | 82% | 97% | 100% |
| Cost | $0 | $0.12 | $0.87 (batch) | $0.07 | $2.20 |

### What it shows

- **The tools matter more than the model.** Haiku 5.5 + MCP matches or beats Opus 5.5 alone on every row, at about 1/16 of the cost ($0.30 vs $4.70 across both sets).
- **Without tools, both models are inconsistent, not just wrong.** Asked the same chart in different words, Haiku gives the same core answer 44% of the time and Opus 74%. With MCP, both are 100%.
- **Most errors without tools are arithmetic.** Interaction detection is near perfect once the pillars are given; the misses come from computing the chart. The rest are Ten God polarity and direction slips (e.g. reading 子's 癸 as yang).
- **The method verdict is a different kind of score.** Strength and favorable elements depend on method; the gold here is this engine's 扶抑 implementation. A low number there means "disagrees with this method", not necessarily "wrong". That's why it's reported separately from chart facts.
- **Haiku + MCP's two edge misses:** one reply had no final answer JSON, and one overrode a correct tool answer. The second was partly caused by ambiguous wording in the question (see [Caveats](#caveats)). Opus + MCP never overrode the tool.

## The engine fix found by this bench

The edge suite's gold comes from [`reference.py`](reference.py), not the engine. It's an independent implementation: solar terms and the equation of time from PyEphem, the day pillar from the Julian day number, and clock time to UTC through the IANA time-zone database. It agrees with `lunar_python` within 0.3 minutes on 66 solar terms and on 400 of 400 sampled day pillars.

Against it, the original engine scored **75%** on `edge-eval`. That exposed two bugs, both now fixed:

| Bug | Where | Effect |
|---|---|---|
| "True solar time" was mean solar time: no equation of time | `core/time_engine.py` | Wrong hour pillar for births near an hour boundary (0% on that category) |
| Local solar time was compared against solar terms kept in Beijing time | `core/time_engine.py` → `core/bazi_math.py` | Births outside UTC+8 within hours of a jie got the wrong year/month pillar and Da Yun timing (70% / 80%) |

After the fix: **100%** on every category, with no change on any other category, and no gold answer in the main suites affected.

## Caveats

- **Main-suite gold comes from the engine.** "Correct" there means "matches the engine". The edge suite is the one that checks the engine itself.
- **One run per arm.** Apart from the stability repeats, each question was asked once, so small differences (e.g. 97% vs 100%, which is 2 of 60 answers) are within noise.
- **Ambiguous wording in `edge-eval`.** The zi-hour convention sentence ("takes the next day's stem for the Hour Pillar") can be read as "use the next day's stem as the hour stem". It means the next day's stem *determines* the hour stem through the 五鼠遁 rule. The set is frozen, so the wording stays; read the 子時 results with that in mind.
- **6 eval questions** were used in early pipeline smoke tests (`results/eval/smoke*`). None of their gold changed.
- **Pinyin answers** (`"Hai"`, `"bingwu"`) are accepted. An earlier version of the scorer silently dropped them, understating every Claude-only arm. All results here are from the fixed scorer.

## How it works

### Suites

| Suite | Question | Scored by |
|---|---|---|
| `accuracy` | One fact from birth data: the day pillar, a stem's Ten God, or a branch's hidden stems | Exact match |
| `stability` | One chart asked 5 ways (3 English, 2 Chinese, different framings), the main wording repeated 3 times | Agreement with itself and match with gold, always shown side by side |
| `interactions` | Every branch interaction (沖合刑害破, three-harmonies), asked from birth data and from the pillars | Set F1 over normalized keys such as `clash:子-午` |
| `edge` | The four pillars for a birth that sits on one edge case | Focus pillar right / all four right |

Every edge case isolates one effect: each boundary that decides it is at least 5 minutes away, and a case is rejected if a second effect could also change the answer.

### Question sets

| Set | Size | Use |
|---|---|---|
| `dev`, `edge-dev` | 73 / 30 records | Debugging prompts and scoring. Regenerable; charts never overlap the eval sets. |
| `eval`, `edge-eval` | 220 / 60 records | Formal results. Frozen: `generate.py` refuses to rewrite them, the runner checks their `.sha256`, and they only run in full. |

## Running it

```bash
pip install -r requirements.txt -r bench/requirements.txt   # bench adds ephem + tzdata
# ANTHROPIC_API_KEY in .env

python -m bench.runner --dry-run                                     # free: prints prompts, checks the MCP server
python -m bench.runner --run try1 --model claude-haiku-5-5           # dev set, claude + mcp arms
python -m bench.runner --set edge-dev --run try1 --arm engine        # engine alone, free
python -m bench.runner --set eval --run v2 --arm claude --batch \
       --model claude-opus-5-5 --max-cost 10                         # formal run, half price via batches

python -m bench.score --set eval --run v2 --failures                 # scorecard + every wrong answer
```

Useful flags:

- `--max-cost N`: stops starting new calls once an arm's estimated spend reaches $N. Re-run the same command to resume.
- `--batch`: sends the `claude` arm through the Message Batches API at half price. Results usually arrive within the hour (at most 24h). Re-running collects a pending batch instead of paying for a new one.
- `--live-geocode`: the MCP arm uses the real Nominatim geocoder instead of the fixed city table the gold was built from.

Prompt caching is on for the `mcp` arm: about 80% of its input tokens are read from cache.

## Layout

```
bench/
├── generate.py      # builds the question sets
├── reference.py     # independent four-pillar reference (edge gold)
├── runner.py        # runs the arms, records raw replies
├── score.py         # grades a run: scores.json + failures.jsonl
├── data/            # dev / eval / edge-dev / edge-eval (+ .sha256 for frozen sets)
└── results/<set>/<run>/
    ├── <arm>.jsonl  # one line per (question, repeat): reply, tool calls, tokens, cost inputs
    ├── scores.json
    └── failures.jsonl
```

Formal runs: `eval/haiku55`, `eval/opus55`, `edge-eval/haiku55`, `edge-eval/opus55`, `edge-eval/engine-fixed` (and `engine-baseline`, before the fix).
