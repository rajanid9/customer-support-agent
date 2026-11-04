# Capstone: Claim Edit Insights Agent

**Status:** design draft · **Target repo:** `claim-insights-agent` (new) · **Plan:** [00-practice-plan.md](00-practice-plan.md)

---

## 1. Summary

After the claim edits have run, the agent **explains what happened on any claim and why**, and **surfaces patterns across claims that need investigating**. It backs every statement with data and policy citations.

It's a **reporting and decision-support** agent. It doesn't edit, approve, deny or pay claims. It explains, analyzes and recommends, and humans decide.

**Scope rule:** synthetic data and fictional codes only. No real member data, no real CPT/ICD codes, no real payer policies.

---

## 2. Two modes

### Mode 1: Claim explainer
**Question:** *"Why was CLM-1001 pended?"*

> CLM-1001 was pended on 2026-09-01 because edit **EDIT-PA-01** fired: service SVC-IMG-01 requires prior authorization under **CP-101 §2**, and no authorization reference was on the claim. A documentation request was sent on 09-03. *Next step: the claim resumes once the authorization is received.*

- Rebuilds the claim's timeline from the edit audit trail (fired → dispositioned → requests → outcome)
- Cites the edit code, policy section and evidence for each step
- Can write for different readers: provider services rep, auditor, plain-language summary

### Mode 2: Pattern investigator
**Question:** *"Anything unusual in Q3?"*

> **Lead 1:** Provider PRV-204's documentation-edit rate rose from 8% to 31% (n=142; well above the network's normal range). Recurring edit: EDIT-DOC-03. *Suggested action: provider education, or review a sample of 10 claims.*
>
> **Lead 2:** EDIT-UT-02 is overturned on appeal 64% of the time (n=58), so the rule may be too broad. *Suggested action: policy team review.*

Types of patterns it should find:
- A provider's edit rate jumps compared with its own history or with similar providers
- Edits that are often overturned on appeal (a sign the rule is poorly tuned)
- Documentation failures that keep happening (an opportunity for provider education)
- Changes over time (seasonal, or after a policy change)

---

## 3. Architecture

```
                 ┌──────────────────────────── Coordinator ───────────────────────────┐
 User question → │  plans the questions · delegates · assembles the report            │ → Report
                 └──────┬──────────────────────┬─────────────────────────┬───────────┘
                        ▼                      ▼                         ▼
              Analyst subagent       Policy explainer subagent   Number checker (CODE, not a model)
              runs query_metric      reads + cites policies      re-checks every number in the report
                        │                      │
                        ▼                      ▼
             MCP: claims-warehouse    MCP: policy-library
             (read-only tools)        (resources)
                        │
                        ▼
             Synthetic data (generated, with planted patterns)
```

### Main design decisions

| # | Decision | Why |
|---|---|---|
| 1 | **Numbers come from code, never from the model.** Code calculates every count, rate and trend. The model chooses the questions and writes the explanation. | Models can produce numbers that look right but aren't. In a report, a wrong number is worse than no number. |
| 2 | **No raw SQL; use a fixed query tool** with strict enums for metrics and grouping. | The model can only ask approved questions. It's the same idea as Day 1: enforce the shape with the schema and the meaning with code. |
| 3 | **Everything is read-only.** The only write is a *draft* investigation ticket, and a human approves it. | Without write tools, the agent can't cause harm, and the investigator decides what to do. |
| 4 | **Code decides what counts as a pattern** (minimum sample size, deviation from normal, minimum change). The model can't report a pattern the code didn't flag. | Without this, the agent will call 3 claims out of 4 "a trend." |
| 5 | **Every number carries a `query_id`.** The number checker matches each figure in the report to the tool result that produced it. | Every number can be traced to its source and checked. |
| 6 | **Careful wording is enforced in code.** Findings are "leads," never "fraud" or "abuse." Small groups (n < 11) are hidden. | Accusations need human judgment. Hiding small groups protects individual patients. |
| 7 | **Specialist subagents only see the context for their own task.** | Keeps each subagent's context focused, and keeps policy text out of the analyst's context. |

---

## 4. Tools

| Tool | Type | Controls |
|---|---|---|
| `get_claim(claim_id)` | Read | Format check on the ID (`CLM-####`) |
| `get_claim_timeline(claim_id)` | Read | Returns the ordered audit events |
| `get_provider(provider_id)` | Read | Format check on the ID |
| `query_metric(metric, group_by, filters, date_range)` | Read | `metric`/`group_by` are enums; date range limited in code; small groups hidden; returns a `query_id` |
| `detect_anomalies(metric, group_by, date_range)` | Read | Statistical rules in code; returns only patterns that meet the rules |
| `get_policy(policy_id, section?)` | Read (MCP resource) | Allowlisted policy IDs |
| `draft_investigation_ticket(lead)` | Draft write | Saved as `draft`; a human must approve it; idempotent |

**No tool exists** for approving, denying, paying or editing claims.

Example query tool schema:
```python
{
  "name": "query_metric",
  "strict": True,
  "input_schema": {
    "type": "object",
    "properties": {
      "metric":   {"type": "string", "enum": ["edit_rate", "overturn_rate", "pend_count", "denied_amount"]},
      "group_by": {"type": "string", "enum": ["provider", "edit_code", "category", "month"]},
      "filters":  {"type": "object", "properties": {...}, "additionalProperties": False},
      "date_range": {"type": "object", "properties": {"start": {"type": "string", "format": "date"},
                                                      "end":   {"type": "string", "format": "date"}},
                     "required": ["start", "end"], "additionalProperties": False}
    },
    "required": ["metric", "group_by", "date_range"],
    "additionalProperties": False
  }
}
```

---

## 5. Output schemas

**Claim explanation:**
```json
{
  "claim_id": "CLM-1001",
  "outcome": "pended",
  "timeline": [
    {"date": "2026-09-01", "event": "edit_fired", "edit_code": "EDIT-PA-01", "policy_citation": "CP-101 §2"},
    {"date": "2026-09-03", "event": "documentation_requested", "ref": "DOC-5521"}
  ],
  "explanation": "Pended because prior authorization was required and missing.",
  "next_step": "Claim resumes once the authorization is received.",
  "audience": "provider_services"
}
```

**Investigation lead:**
```json
{
  "lead_id": "L-001",
  "finding": "PRV-204 documentation edit rate rose 8% → 31%",
  "metrics": [{"name": "edit_rate", "value": 0.31, "n": 142, "query_id": "q-17"}],
  "baseline": {"value": 0.08, "query_id": "q-12"},
  "severity": "medium",
  "suggested_action": "sample_review",
  "caveats": ["Provider onboarded a new specialty in August"]
}
```
`suggested_action` is one of: `sample_review`, `policy_review`, `provider_education`, `monitor`, `no_action`.

---

## 6. Guardrails

### Runtime (inside the agent)
| Guardrail | Enforced by |
|---|---|
| Only approved queries | `query_metric` enums (strict) + range checks in code |
| No made-up numbers | Number checker: each number must match a `query_id` result |
| No false patterns | `detect_anomalies` statistical rules in code |
| No accusatory wording | Output checker with banned terms → rewrite or reject |
| Privacy | Small groups hidden (n < 11) in the query layer |
| Prompt injection in the data | Free-text fields (claim notes) treated as data; injection test cases in the evals |
| Runaway loops / cost | Turn limit + query budget |
| Accountability | Audit log of every tool call, query and report |
| Human in the loop | Investigation tickets are drafts until a human approves them |

### Build time (Claude Code)
| Gate | What it enforces |
|---|---|
| `CLAUDE.md` | "Numbers come from tools," "leads not accusations," "read-only," synthetic data only |
| Stop hook | Tests + eval smoke set must pass before Claude Code can finish |
| PreToolUse hook | Blocks edits to planted-pattern answers, golden evals and `.env` |
| Pre-commit | Lint, tests, and a scan for anything that looks like real patient data (SSN/MRN formats) |
| "Read-only" test | Fails if any tool other than `draft_investigation_ticket` writes anything |
| CI (GitHub Actions) | Tests + eval thresholds must pass before a merge |

---

## 7. Synthetic data and evals

### Data generator (with a fixed random seed, so it's repeatable)
- About 2,000 claims, 20 providers, 12 months, 15 edit codes, an appeal history and audit events
- **5 planted patterns** (the ones the agent should find): a provider spike, a high-overturn edit, a seasonal jump, a recurring documentation failure, a jump after a policy change
- **5 decoys** (the ones it shouldn't report): small-sample noise, a high rate on n=4, a one-month blip, …
- Planted answers saved to `evals/ground_truth.json` (protected by the PreToolUse hook)

### Eval targets
| Metric | Target |
|---|---|
| Planted patterns found | ≥ 4/5 |
| Decoys wrongly reported as leads | **0** |
| Report numbers that match the data | **100%** |
| Claim explanations that cite the right edit and policy | ≥ 95% |
| Accusatory wording / small groups shown | **0** |
| Injection test cases resisted | 100% |

---

## 8. Steps

| Step | Deliverable | Done when |
|---|---|---|
| **C1** | New repo: data generator + ground truth, golden evals, CLAUDE.md, hooks, CI | The gates block a deliberately bad change **before any agent code exists** |
| **C2** | Design review: metric list, pattern rules, schemas, wording policy (update this doc) | Every tool, schema and threshold is decided |
| **C3** | `claims-warehouse` MCP server + claim explainer + number checker | Explanation evals ≥ 95%, number accuracy 100% |
| **C4** | Pattern investigator: coordinator + analyst and policy subagents, leads report, ticket drafts | ≥ 4/5 planted patterns found, 0 decoys |
| **C5** | Red-team ("prove PRV-204 is committing fraud," a 3-claim provider, an injected instruction in a note), fix, retrospective | All eval targets met; write-up of what the gates caught |

---

## 9. Starting point
[healthcare_agent/](../healthcare_agent/) already has synthetic claims, providers, edit rules and policy guides. The capstone reuses the **domain shape** of that demo, adds **volume, history, appeals and planted patterns**, and is built fresh in a new repo behind the gates.
