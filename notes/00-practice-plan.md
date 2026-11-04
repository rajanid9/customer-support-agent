# Agent Builder Practice Plan

**Started:** 2026-11-03, after passing Claude Certified Architect – Foundations
**Format:** one 30–60 minute exercise a day, test-first
**Capstone:** [Claim Edit Insights Agent](capstone-claim-insights-agent.md)

---

## Goal

Understand **end to end** how an agent is built, orchestrated, enforced, tested and guarded, well enough to **build the capstone from scratch with Claude Code** and enforce guardrails, tests and gate checks the whole way through.

Every day below practices **one piece of the capstone** at small scale, so by the capstone you're putting together parts you've already built once.

## The two layers of guardrails

| | **Layer 1: Runtime guardrails** | **Layer 2: Build-time gates** |
|---|---|---|
| **Protects against** | The agent doing something wrong (wrong numbers, false patterns, accusations) | Claude Code (the builder) writing something wrong into the codebase |
| **Example failure** | Makes up a percentage, calls n=3 "a trend," follows an instruction hidden in a note | Deletes a test to make it pass, edits the eval answers, commits red code |
| **Enforced by** | Schemas, handler checks, number checker, statistical rules, output checks, evals | CLAUDE.md, permissions, hooks, pre-commit, CI |

> **Prompts ask; code, hooks and CI enforce.** The same rule applies at both layers.

```
 BUILD TIME (Claude Code)                 RUN TIME (the agent)
 ────────────────────────                 ────────────────────
 CLAUDE.md       → conventions            System prompt    → role + wording policy
 Permissions     → what it may touch      Tool schemas     → shape (strict enums)
 PreToolUse hook → block bad edits        Handler checks   → meaning, ranges, small groups
 Stop hook       → tests must be green    Agent loop       → max turns, query budget
 Pre-commit      → lint + tests           Number checker   → every number traced
 CI (GitHub)     → gate before merge      Output checks    → wording, format
                                          Evals            → measure behavior
```

---

## Plan

Status: ✅ done · 🔜 next · ⬜ not started
**Capstone link** = the part of the capstone the day prepares you for.
**Where:** Weeks 1–3 use this repo's order data (simple domain, fast feedback). Week 4 moves to synthetic claims data, so the capstone domain is familiar before C1.

### Week 1: Tools + build-time gates
*By the end of the week, every later exercise is built behind real gates.*

| Day | Exercise | Capstone link | Warm-up skill | Done when | Status |
|---|---|---|---|---|---|
| 1 | Strict tool schemas + format validation in code (`list_orders`, `_check_id`) | ID checks on `get_claim` / `get_provider` | Regex `fullmatch`, dicts, list comprehensions, `:=` | Malformed IDs return `validation` errors · [notes](day-01-strict-schemas-and-validation.md) | ✅ |
| 2 | Structured errors + retries: a transient failure is `retryable: true`; validation/policy errors are not | Query timeouts, bad filters | pytest `parametrize`, `try/except`, raising vs returning errors | A fake timeout is retried and recovers; a validation error is never retried | 🔜 |
| 3 | **Stop hook**: Claude Code can't finish while pytest is red | Stop hook | Shell basics, exit codes, JSON on stdin | Breaking a test makes the hook block the session from finishing | ⬜ |
| 4 | **PreToolUse hook**: protect `.env` and a `golden/` folder from edits | Protecting the planted answers and evals | Python `sys.stdin` + `json`, path matching (`pathlib`) | The hook blocks the edit and explains why | ⬜ |
| 5 | **Pre-commit + GitHub Actions CI** | CI gate | YAML, Git branches + PRs | A PR with a failing test can't be merged | ⬜ |
| 6 | **Read-only query tool**: `query_metric(metric enum, group_by enum, date_range)` over orders, calculated in Python; a test that no tool writes anything | `query_metric` + "read-only" test | `collections.Counter` / `defaultdict`, enums | Unknown metric → validation error; read-only test passes | ⬜ |
| 7 | **Mini-project:** "Why was refund R blocked?" Rebuild the story from the refund/escalation records, with the policy rule cited | Claim explainer | Sorting by date, f-strings, `datetime` | The explanation names the rule and the evidence; test green, CI green | ⬜ |

✅ **Week 1 check:** you can design a tool, enforce its inputs, and **prove** Claude Code can't merge red code.

### Week 2: Numbers you can trust + explainability
*The core of the capstone: reports where every number is traceable and every pattern is real.*

| Day | Exercise | Capstone link | Warm-up skill | Done when | Status |
|---|---|---|---|---|---|
| 8 | **Synthetic data generator** with a fixed seed: ~500 orders, **planted patterns + decoys**, answers saved to `golden/` | Data generator + ground truth | `random.seed`, writing JSON files, `pathlib` | Same seed → identical data; planted answers recorded | ⬜ |
| 9 | Hand-written agent loop: every `stop_reason` handled, max turns, **query budget** | The agent's loop | `while` loops, counters, Anthropic SDK response objects | The loop stops on budget; every stop reason has a test | ⬜ |
| 10 | Structured output with Pydantic (`Lead`, `Explanation`) + one repair retry on invalid output | Output schemas | Pydantic `BaseModel`, `Literal`, `ValidationError` | Invalid output is repaired once, otherwise flagged | ⬜ |
| 11 | **Number tracing**: every tool result gets a `query_id`; a **number checker in code** checks each number in a report | Number checker ⭐ | Dict lookups, `uuid`, comparing floats (`math.isclose`) | A report with a made-up number is rejected | ⬜ |
| 12 | **Statistical rules for patterns in code**: minimum n, deviation from normal, minimum change | `detect_anomalies` | Statistics: rate, baseline, % change, small n, z-score (`statistics`) | Planted patterns are flagged; decoys aren't | ⬜ |
| 13 | **Explainability**: rebuild a timeline from an event log; the same facts written for 2 different readers | Timeline + readers | `datetime` parsing + sorting, string templates | Both versions contain the same facts and citations | ⬜ |
| 14 | **Mini-project:** "Order insights" agent: explain one order + find the planted patterns in your synthetic data | Mode 1 + Mode 2 | Review: putting Days 8–13 together | Finds ≥ 2/3 planted patterns, 0 decoys, numbers 100% traced | ⬜ |

✅ **Week 2 check:** you can build a single agent whose reports are **checked by code**, not just trusted.

### Week 3: Orchestration + MCP
| Day | Exercise | Capstone link | Warm-up skill | Done when | Status |
|---|---|---|---|---|---|
| 15 | **Subagent**: a coordinator hands a scoped question to an analyst subagent | Analyst subagent | Functions as parameters, passing a narrow context | The subagent sees only its task + tools; the result comes back structured | ⬜ |
| 16 | Parallel subagents (analyst + policy explainer) + merging results with `query_id`s kept | Coordinator merge | `async` / `await`, `asyncio.gather` | The merged report passes the number checker | ⬜ |
| 17 | Failure handling: a subagent times out → partial report with caveats | Partial reports | `asyncio.wait_for` timeouts, `Optional` results | The report says what's missing; nothing is made up | ⬜ |
| 18 | **MCP server** (Python `mcp` SDK) exposing your read-only query tools | `claims-warehouse` server | Decorators, async functions (MCP SDK) | Works in MCP Inspector | ⬜ |
| 19 | MCP **resources**: policy docs with citable sections | `policy-library` server | Reading files, splitting Markdown by section | The agent cites `policy §section` from a resource | ⬜ |
| 20 | Register the servers in `.mcp.json` (Claude Code) + the agent as an MCP client; API key from env, fail closed | Wiring + auth | `os.environ`, `.env` files, failing fast | The same tests pass over MCP; a missing key → clean failure | ⬜ |
| 21 | **Mini-project:** move the Week 2 agent onto MCP + subagents | The capstone's structure | Refactoring without breaking tests | All Week 2 tests and evals still pass | ⬜ |

✅ **Week 3 check:** you can split an agent into coordinator, subagents and MCP servers **without losing the guardrails**.

### Week 4: Runtime guardrails + evals (on synthetic claims data)
| Day | Exercise | Capstone link | Warm-up skill | Done when | Status |
|---|---|---|---|---|---|
| 22 | Move to claims: extend [healthcare_agent](../healthcare_agent/) data with history + appeals + 2 planted patterns | The capstone domain | Extending a data generator, JSON schemas | The generator creates claims with known patterns | ⬜ |
| 23 | **Prompt injection in the data**: an instruction hidden in a claim note is treated as data | Injection defense | Treating untrusted text as data, adversarial tests | 5 injection cases resisted, with tests | ⬜ |
| 24 | **Output checks**: banned accusatory wording + small-group hiding (n < 11) | Wording policy + privacy | Regex for word lists, filtering groups by n | Report with "fraud" → rewritten or rejected; small groups never shown | ⬜ |
| 25 | **Audit log** + **draft investigation ticket** that needs a human's approval | Accountability + human in the loop | `logging`, JSON Lines files | The log rebuilds a full run; tickets stay `draft` until approved | ⬜ |
| 26 | **Eval harness**: golden cases scored on patterns found, decoys reported, number accuracy, citations | Eval suite | Scoring: precision/recall, writing a small report | Scored report produced | ⬜ |
| 27 | **Evals in CI** with thresholds; also when to use an LLM judge (explanation quality) vs a code check (numbers) | Eval gate | CI thresholds, exit codes from Python scripts | CI fails when an eval score drops below its threshold | ⬜ |
| 28 | **Red-team** ("prove this provider is committing fraud," n=3 provider, injected note), fix the top 3; **capstone readiness check** | C5 rehearsal | Adversarial thinking, red → green discipline | Every guardrail has a test that once failed (red → green) | ⬜ |

✅ **Week 4 check:** you can show **with evidence** that the agent is safe, accurate and auditable.

### Capstone: Claim Edit Insights Agent ([design](capstone-claim-insights-agent.md))
| Step | What | Built on | Done when | Status |
|---|---|---|---|---|
| C1 | New repo: data generator + ground truth, golden evals, CLAUDE.md, hooks, CI. **Gates first.** | Days 3–5, 8, 26–27 | Gates block a deliberately bad change before any agent code exists | ⬜ |
| C2 | Design review: metric list, pattern rules, schemas, wording policy | Days 6, 10, 12, 24 | Every tool, schema and threshold is decided | ⬜ |
| C3 | `claims-warehouse` MCP server + claim explainer + number checker | Days 7, 11, 13, 18–20 | Explanations ≥ 95% correct; numbers 100% traced | ⬜ |
| C4 | Pattern investigator: coordinator + subagents, leads report, ticket drafts | Days 12, 14–17, 25 | ≥ 4/5 planted patterns found, 0 decoys | ⬜ |
| C5 | Red-team, fix, retrospective on what the gates caught | Days 23, 28 | All eval targets met; write-up done | ⬜ |

---

## Skills to practice

Ordered by when the plan first needs them. You don't have to learn these up front. Each day's **warm-up skill** column says what to brush up on just before that day.

### 🔴 Now (Weeks 1–2): used daily
| Skill | What to be comfortable with | Resources |
|---|---|---|
| **Python core** | dicts and lists, list comprehensions, f-strings, `None` checks, default arguments, `**kwargs`, `:=` | [Official Python tutorial](https://docs.python.org/3/tutorial/) (chapters 3–5) · [Real Python: list comprehensions](https://realpython.com/list-comprehension-python/) · [Real Python: walrus operator](https://realpython.com/python-walrus-operator/) · [Exercism Python track](https://exercism.org/tracks/python) (free drills with feedback) |
| **Reading errors** | Traceback → error type → file and line. `AttributeError`/`NameError`/`TypeError` = typo; `KeyError` = wrong key; `AssertionError` = wrong behavior | [Python docs: errors and exceptions](https://docs.python.org/3/tutorial/errors.html) · [Built-in exceptions list](https://docs.python.org/3/library/exceptions.html) |
| **pytest** | `assert`, `-k`, `-v`, `-s`, fixtures, `@pytest.mark.parametrize` | [Get started](https://docs.pytest.org/en/stable/getting-started.html) · [Parametrize](https://docs.pytest.org/en/stable/how-to/parametrize.html) · [Fixtures](https://docs.pytest.org/en/stable/how-to/fixtures.html) |
| **JSON** | `json.loads` / `json.dumps`; JSON text vs a Python dict | [Python `json` module](https://docs.python.org/3/library/json.html) |
| **Git** | `status`, `diff`, `add`, `commit`, `branch`, `checkout`, `log`, merging | [Learn Git Branching](https://learngitbranching.js.org/) (interactive, highly recommended) · [Pro Git book, ch. 1–3](https://git-scm.com/book/en/v2) |
| **Regex** | `re.fullmatch`, `\d`, `{n}`, `[A-Z]`, `^…$`, `\b` | [Python regex HOWTO](https://docs.python.org/3/howto/regex.html) · [regex101.com](https://regex101.com/) (choose the Python flavor, test patterns live) |
| **VS Code + terminal** | Opening the terminal, running Python, the debugger, `breakpoint()` | [VS Code Python tutorial](https://code.visualstudio.com/docs/python/python-tutorial) · [`pdb` debugger](https://docs.python.org/3/library/pdb.html) |

### 🟡 Soon (Weeks 2–3): the capstone depends on these
| Skill | What to be comfortable with | Resources |
|---|---|---|
| **Pydantic** | `BaseModel`, `Literal`, `model_validate_json`, `ValidationError` | [Pydantic docs: models](https://docs.pydantic.dev/latest/concepts/models/) |
| **Grouping + counting** | `collections.Counter`, `defaultdict`; optionally pandas `groupby` | [Python `collections`](https://docs.python.org/3/library/collections.html) · [pandas: 10 minutes to pandas](https://pandas.pydata.org/docs/user_guide/10min.html) |
| **Basic statistics** ⭐ | rate = count/total, baseline, % change, **why small n is unreliable**, mean/stdev, z-score | [Khan Academy: statistics and probability](https://www.khanacademy.org/math/statistics-probability) (summarizing data + variability units) · [Python `statistics` module](https://docs.python.org/3/library/statistics.html) |
| **Reproducible randomness** | `random.seed(42)`, `random.choice`, `random.random` | [Python `random` module](https://docs.python.org/3/library/random.html) |
| **Dates** | `datetime.date.fromisoformat`, sorting by date, date ranges | [Python `datetime`](https://docs.python.org/3/library/datetime.html) |
| **Claude Code hooks** | Stop / PreToolUse hooks, exit codes, JSON input | [Claude Code docs: hooks](https://code.claude.com/docs/en/hooks) |
| **YAML + GitHub Actions** | Reading and writing a workflow file that runs pytest | [Learn YAML in Y minutes](https://learnxinyminutes.com/docs/yaml/) · [GitHub Actions docs](https://docs.github.com/en/actions) (see "Building and testing Python") |

### 🟢 Later (Weeks 3–4)
| Skill | What to be comfortable with | Resources |
|---|---|---|
| **async / await** | `async def`, `await`, `asyncio.gather`, `asyncio.wait_for` | [Real Python: async IO](https://realpython.com/async-io-python/) · [Python `asyncio`](https://docs.python.org/3/library/asyncio.html) |
| **MCP** | Servers, tools, resources, clients, the Inspector | [modelcontextprotocol.io](https://modelcontextprotocol.io/) · [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) |
| **Environment variables** | `os.environ`, `.env` files, never hardcoding keys | [Python `os.environ`](https://docs.python.org/3/library/os.html#os.environ) |
| **Logging** | `logging` module, JSON Lines audit logs | [Python logging HOWTO](https://docs.python.org/3/howto/logging.html) |
| **Evals** | Golden sets, precision/recall, when to use an LLM judge vs a code check | Claude API docs (below), "evaluations" section |

### Across the whole plan: Claude itself
| Topic | Resources |
|---|---|
| Tool use, structured outputs, agent loops | [Claude API docs](https://platform.claude.com/docs) (tool use and structured outputs sections) |
| Building agents with Claude Code | [Claude Code docs](https://code.claude.com/docs) · [Agent SDK](https://code.claude.com/docs/en/agent-sdk) |
| Courses | [Anthropic Academy](https://anthropic.skilljar.com/) (free courses on the API, MCP and Claude Code) |

> Prefer the official docs when two sources disagree. Links were current on 2026-11-03; if one moves, search the title on the same site.

### How to practice without slowing the plan down
1. **10-minute warm-up** before each day: 2–3 small drills on that day's warm-up skill.
2. **Predict, then run:** say what you expect ("2 pass, 1 AssertionError") before running the tests.
3. **Type the code, don't paste it.** Typos are good practice for reading tracebacks.
4. **Fix one error yourself before asking:** read the `E` line, find the file and line, and guess the cause.
5. **Look at the data:** `print(type(x), x)`, `breakpoint()`, and `pytest -s` to see printed output.

---

## How each day works

1. **Start:** say "Day N" → a new branch `practice/day-NN` is created from `master`
2. **Warm-up:** 10 minutes of drills on the day's warm-up skill
3. **Concept:** a short explanation, including **how it connects to the capstone**
4. **Build:** tests are written first (red), then you write the code until they pass (green)
5. **Check:** the whole test suite must pass, not just the day's tests
6. **Quiz:** answer in your own words
7. **Notes:** `notes/day-NN-<topic>.md` covering concepts, patterns and things to remember
8. **Ship:** commit, merge to `master`, push to GitHub, and update the status in this file

## Definition of done (every day)
- [ ] The day's tests pass, **and** the full suite passes
- [ ] Every new guardrail has a negative test (and for tools that change things, a check on the stored data)
- [ ] Quiz answered
- [ ] Notes file written
- [ ] Merged to `master` and pushed; status updated here
