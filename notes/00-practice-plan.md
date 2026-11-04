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

| Day | Exercise | Capstone link | Done when | Status |
|---|---|---|---|---|
| 1 | Strict tool schemas + format validation in code (`list_orders`, `_check_id`) | ID checks on `get_claim` / `get_provider` | Malformed IDs return `validation` errors · [notes](day-01-strict-schemas-and-validation.md) | ✅ |
| 2 | Structured errors + retries: a transient failure is `retryable: true`; validation/policy errors are not | Query timeouts, bad filters | A fake timeout is retried and recovers; a validation error is never retried | 🔜 |
| 3 | **Stop hook**: Claude Code can't finish while pytest is red | Stop hook | Breaking a test makes the hook block the session from finishing | ⬜ |
| 4 | **PreToolUse hook**: protect `.env` and a `golden/` folder from edits | Protecting the planted answers and evals | The hook blocks the edit and explains why | ⬜ |
| 5 | **Pre-commit + GitHub Actions CI** | CI gate | A PR with a failing test can't be merged | ⬜ |
| 6 | **Read-only query tool**: `query_metric(metric enum, group_by enum, date_range)` over orders, calculated in Python; a test that no tool writes anything | `query_metric` + "read-only" test | Unknown metric → validation error; read-only test passes | ⬜ |
| 7 | **Mini-project:** "Why was refund R blocked?" Rebuild the story from the refund/escalation records, with the policy rule cited | Claim explainer | The explanation names the rule and the evidence; test green, CI green | ⬜ |

✅ **Week 1 check:** you can design a tool, enforce its inputs, and **prove** Claude Code can't merge red code.

### Week 2: Numbers you can trust + explainability
*The core of the capstone: reports where every number is traceable and every pattern is real.*

| Day | Exercise | Capstone link | Done when | Status |
|---|---|---|---|---|
| 8 | **Synthetic data generator** with a fixed seed: ~500 orders, **planted patterns + decoys**, answers saved to `golden/` | Data generator + ground truth | Same seed → identical data; planted answers recorded | ⬜ |
| 9 | Hand-written agent loop: every `stop_reason` handled, max turns, **query budget** | The agent's loop | The loop stops on budget; every stop reason has a test | ⬜ |
| 10 | Structured output with Pydantic (`Lead`, `Explanation`) + one repair retry on invalid output | Output schemas | Invalid output is repaired once, otherwise flagged | ⬜ |
| 11 | **Number tracing**: every tool result gets a `query_id`; a **number checker in code** checks each number in a report | Number checker ⭐ | A report with a made-up number is rejected | ⬜ |
| 12 | **Statistical rules for patterns in code**: minimum n, deviation from normal, minimum change | `detect_anomalies` | Planted patterns are flagged; decoys aren't | ⬜ |
| 13 | **Explainability**: rebuild a timeline from an event log; the same facts written for 2 different readers | Timeline + readers | Both versions contain the same facts and citations | ⬜ |
| 14 | **Mini-project:** "Order insights" agent: explain one order + find the planted patterns in your synthetic data | Mode 1 + Mode 2 | Finds ≥ 2/3 planted patterns, 0 decoys, numbers 100% traced | ⬜ |

✅ **Week 2 check:** you can build a single agent whose reports are **checked by code**, not just trusted.

### Week 3: Orchestration + MCP
| Day | Exercise | Capstone link | Done when | Status |
|---|---|---|---|---|
| 15 | **Subagent**: a coordinator hands a scoped question to an analyst subagent | Analyst subagent | The subagent sees only its task + tools; the result comes back structured | ⬜ |
| 16 | Parallel subagents (analyst + policy explainer) + merging results with `query_id`s kept | Coordinator merge | The merged report passes the number checker | ⬜ |
| 17 | Failure handling: a subagent times out → partial report with caveats | Partial reports | The report says what's missing; nothing is made up | ⬜ |
| 18 | **MCP server** (Python `mcp` SDK) exposing your read-only query tools | `claims-warehouse` server | Works in MCP Inspector | ⬜ |
| 19 | MCP **resources**: policy docs with citable sections | `policy-library` server | The agent cites `policy §section` from a resource | ⬜ |
| 20 | Register the servers in `.mcp.json` (Claude Code) + the agent as an MCP client; API key from env, fail closed | Wiring + auth | The same tests pass over MCP; a missing key → clean failure | ⬜ |
| 21 | **Mini-project:** move the Week 2 agent onto MCP + subagents | The capstone's structure | All Week 2 tests and evals still pass | ⬜ |

✅ **Week 3 check:** you can split an agent into coordinator, subagents and MCP servers **without losing the guardrails**.

### Week 4: Runtime guardrails + evals (on synthetic claims data)
| Day | Exercise | Capstone link | Done when | Status |
|---|---|---|---|---|
| 22 | Move to claims: extend [healthcare_agent](../healthcare_agent/) data with history + appeals + 2 planted patterns | The capstone domain | The generator creates claims with known patterns | ⬜ |
| 23 | **Prompt injection in the data**: an instruction hidden in a claim note is treated as data | Injection defense | 5 injection cases resisted, with tests | ⬜ |
| 24 | **Output checks**: banned accusatory wording + small-group hiding (n < 11) | Wording policy + privacy | Report with "fraud" → rewritten or rejected; small groups never shown | ⬜ |
| 25 | **Audit log** + **draft investigation ticket** that needs a human's approval | Accountability + human in the loop | The log rebuilds a full run; tickets stay `draft` until approved | ⬜ |
| 26 | **Eval harness**: golden cases scored on patterns found, decoys reported, number accuracy, citations | Eval suite | Scored report produced | ⬜ |
| 27 | **Evals in CI** with thresholds; also when to use an LLM judge (explanation quality) vs a code check (numbers) | Eval gate | CI fails when an eval score drops below its threshold | ⬜ |
| 28 | **Red-team** ("prove this provider is committing fraud," n=3 provider, injected note), fix the top 3; **capstone readiness check** | C5 rehearsal | Every guardrail has a test that once failed (red → green) | ⬜ |

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

## How each day works

1. **Start:** say "Day N" → a new branch `practice/day-NN` is created from `master`
2. **Concept:** a short explanation, including **how it connects to the capstone**
3. **Build:** tests are written first (red), then you write the code until they pass (green)
4. **Check:** the whole test suite must pass, not just the day's tests
5. **Quiz:** answer in your own words
6. **Notes:** `notes/day-NN-<topic>.md` covering concepts, patterns and things to remember
7. **Ship:** commit, merge to `master`, push to GitHub, and update the status in this file

## Definition of done (every day)
- [ ] The day's tests pass, **and** the full suite passes
- [ ] Every new guardrail has a negative test (and for tools that change things, a check on the stored data)
- [ ] Quiz answered
- [ ] Notes file written
- [ ] Merged to `master` and pushed; status updated here
