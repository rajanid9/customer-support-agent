# Agent Builder Practice Plan

**Started:** 2026-11-03, after passing Claude Certified Architect – Foundations
**Format:** one 30–60 minute exercise a day, built on this repo, test-first

---

## Goal

Understand **end to end** how an agent is built, orchestrated, enforced, tested and guarded, well enough to **build a new agent from scratch with Claude Code** and enforce guardrails, tests and gate checks the whole way through.

## The two layers of guardrails

| | **Layer 1: Runtime guardrails** | **Layer 2: Build-time gates** |
|---|---|---|
| **Protects against** | The agent doing something wrong **for a customer** | Claude Code (the builder) writing something wrong **into the codebase** |
| **Example failure** | Refunds $749, leaks a card number, loops forever | Deletes a test to make it pass, skips validation, commits red code |
| **Enforced by** | Schemas, handler checks, policy code, escalation, max turns, evals | CLAUDE.md, permissions, hooks, pre-commit, CI |

> **Prompts ask; code, hooks and CI enforce.** The same rule applies at both layers.

```
 BUILD TIME (Claude Code)                 RUN TIME (the agent)
 ────────────────────────                 ────────────────────
 CLAUDE.md       → conventions            System prompt   → role + policy
 Permissions     → what it may touch      Tool schemas    → shape (strict)
 PreToolUse hook → block bad edits        Handler checks  → meaning + policy
 Stop hook       → tests must be green    Agent loop      → max turns, stop reasons
 Pre-commit      → lint + tests           Output guard    → PII, format
 CI (GitHub)     → gate before merge      Escalation      → human in the loop
                                          Evals           → measure behavior
```

---

## Plan

Status: ✅ done · 🔜 next · ⬜ not started

### Week 1: Tools + build-time gates
| Day | Exercise | Layer | Done when | Status |
|---|---|---|---|---|
| 1 | Strict tool schemas + format validation in code (`list_orders`, `_check_id`) | Runtime | Malformed IDs return `validation` errors; 27 tests green · [notes](day-01-strict-schemas-and-validation.md) | ✅ |
| 2 | Structured errors + retries: transient failures `retryable: true`, policy errors never retried | Runtime | A fake timeout is retried and recovers; a policy error is escalated, not retried | 🔜 |
| 3 | **Claude Code Stop hook** that runs pytest, so the session can't finish with red tests | Build | Breaking a test makes the hook block the session from finishing | ⬜ |
| 4 | **PreToolUse hook**: block edits to `.env` and test files that would weaken assertions | Build | The hook blocks the edit and explains why | ⬜ |
| 5 | **Pre-commit + GitHub Actions CI**: tests and lint run on every push and PR | Build | A PR with a failing test can't be merged | ⬜ |
| 6–7 | **Mini-project:** end-to-end refund flow built behind the gates from days 3–5 | Both | End-to-end test green, CI green | ⬜ |

### Week 2: Agent loop + orchestration
| Day | Exercise | Done when | Status |
|---|---|---|---|
| 8 | Hand-written agent loop: `stop_reason` handling, max-iteration guard | The loop can't run forever; every stop reason is handled | ⬜ |
| 9 | Context management: trim or summarize old turns past a token budget | A 30-turn conversation stays under budget | ⬜ |
| 10 | Structured final output (Pydantic) with validation, plus one repair retry | Invalid output is repaired once, then escalated | ⬜ |
| 11 | Subagent: a coordinator hands a scoped task to a "policy research" subagent | The subagent sees only the context it needs | ⬜ |
| 12 | Parallel subagents + merging results, with sources kept | The merged answer cites which subagent each part came from | ⬜ |
| 13 | Failure handling: a subagent times out and the coordinator degrades gracefully | Partial answer plus a flag saying what's missing | ⬜ |
| 14 | Compare the hand-written loop with the Tool Runner / Agent SDK | Tradeoffs written up in notes | ⬜ |

### Week 3: MCP
| Day | Exercise | Done when | Status |
|---|---|---|---|
| 15 | MCP server (Python `mcp` SDK) exposing the order tools | Works in MCP Inspector | ⬜ |
| 16 | Add **resources** (refund policy) and a **prompt** template | Readable from Claude Code | ⬜ |
| 17 | Register the server in `.mcp.json` and use it from Claude Code | Claude Code calls your tool | ⬜ |
| 18 | Auth: API key from env, fail closed, no hardcoded secrets | Missing key → clean startup failure | ⬜ |
| 19 | The agent becomes an MCP client, replacing its local tools | Same tests pass over MCP | ⬜ |
| 20–21 | **Mini-project:** ticketing MCP server (create, update, escalate) | The agent escalates a ticket end to end | ⬜ |

### Week 4: Runtime guardrails + evals
| Day | Exercise | Done when | Status |
|---|---|---|---|
| 22 | Input guard: prompt injection and off-topic requests | 10 adversarial prompts are blocked or deflected | ⬜ |
| 23 | Output guard: PII redaction (cards, SSNs) | Redaction tests pass | ⬜ |
| 24 | Approval gate: high-value actions pause for a human | Refunds over $X return `pending_approval` | ⬜ |
| 25 | Escalation triggers + a structured handoff payload | The handoff validates against its schema | ⬜ |
| 26 | Audit log: every tool call recorded with its input, result and decision | The log reconstructs a full conversation | ⬜ |
| 27 | Eval harness: 20 golden cases (correctness, safety, escalation) | Scored report | ⬜ |
| 28 | Red-team your own agent and fix the top 3 issues | Eval score improves | ⬜ |

### Capstone: build a new agent from scratch with Claude Code
| Step | What | Done when | Status |
|---|---|---|---|
| C1 | New repo. Write **gates first**: CLAUDE.md, Stop/PreToolUse hooks, CI, eval cases | Gates block a deliberately bad change before any agent code exists | ⬜ |
| C2 | Design: tool specs, policies, escalation matrix, failure modes | Design doc reviewed | ⬜ |
| C3–C4 | Claude Code builds the agent **behind the gates** | CI green, evals passing | ⬜ |
| C5 | Red-team, fix, write up what the gates caught | Retrospective in notes | ⬜ |

---

## How each day works

1. **Start:** say "Day N" → a new branch `practice/day-NN` is created from `master`
2. **Concept:** a short explanation of the idea behind the day
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
