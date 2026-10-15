# Healthcare Claims Agentic-Loop Demo

This is a learning demo for tool use over synthetic claims. It is not a real claims-processing system and does not encode clinical, coverage, or medical-necessity rules.

## Files

- `claims.json` contains 30 synthetic claims. Each record has claim, member, and provider IDs; service details; a mock status; and an `edits_fired` array. The dataset contains 35 fired edits total.
- `providers.json` contains six synthetic provider records. Claims refer to these records using `provider_id`.
- `edit_rules/` contains five short Markdown workflow guides: `authorization`, `documentation`, `utilization`, `coding_provider`, and `coverage_demographics`.
- `agent.py` loads the JSON files relative to its own path, indexes claims and providers by ID, defines tool schemas and handlers, and runs the model/tool loop.
- `tests/test_agent.py` tests the JSON links, rule lookup, mock-action safeguards, provider counts, and loop behavior with a fake client.

Each fired edit has an `edit_id`, `edit_code`, `policy_id`, `rule_key`, `category`, `disposition`, and explanatory note. `rule_key` connects an edit to a file in `edit_rules/`; `policy_id` is a fictional identifier for the sample.

## Tool Design

The `TOOLS` list describes the tools and input schemas sent to Claude. It is the interface the model can request; it does not execute the work.

`HANDLERS` maps each tool name to a Python function. `execute_tool` dispatches Claude's request to the handler and packages its result or error for the model.

- `get_claim` retrieves one claim and its edits.
- `get_provider` retrieves a provider record.
- `summarize_provider_edits` deterministically counts fired edits by `rule_key` and category for a provider, and returns claim IDs and rule keys to read.
- `get_edit_policy` reads a known Markdown guide selected through an allowlisted `rule_key` mapping.
- `request_documentation` queues an in-memory mock request only when the edit disposition is `information_needed` and the edit belongs to the claim.
- `create_review_task` queues an in-memory mock human-review task for an edit attached to the claim.

The two queue tools only append to Python lists for the current process. They do not contact providers, persist data, or change claim status.

## Agentic Loop

1. `run_agent` starts with the user's request and sends it to Claude along with `TOOLS` and `SYSTEM_PROMPT`.
2. On the first model call, `tool_choice` is `any`, requiring a tool call. Later calls use `auto`, allowing another tool request or a final answer.
3. When Claude returns `stop_reason == "tool_use"`, the loop executes every requested handler and returns all results in one user message, paired with their `tool_use_id` values.
4. Claude sees those results on the next call and can request more tools. It may request independent lookups in the same turn.
5. When Claude returns `stop_reason == "end_turn"`, the loop returns its text. `MAX_TURNS` caps the loop to guard against runaway calls.

The model chooses tools; Python handlers perform deterministic lookups, counting, validation, and mock queueing. Tool descriptions and the system prompt guide behavior, while handler checks enforce important constraints in code.

## Prompt And Boundaries

`SYSTEM_PROMPT` sets the role and boundaries: records are synthetic; retrieve relevant records and read the matching rule guide; never decide coverage or medical necessity; never approve, deny, or alter a claim; and clearly label mock actions.

A useful provider-frequency exercise:

> For provider PRV-201, find which edit rule fires most often across the sample claims. Show the counts and claim IDs, then read and summarize the guidance for every rule that fired for this provider. Do not change any claim or queue a task.

The summary handler should report `utilization` as the top rule for `PRV-201`, with two fired edits (CLM-1007 and CLM-1019). Claude can then call `get_edit_policy` for each distinct returned rule key. Multiple independent policy lookups may be grouped into one model turn.

## Run And Test

From the repository root:

```bash
./.venv/bin/python -m healthcare_agent.agent
./.venv/bin/python -m pytest healthcare_agent/tests/test_agent.py -q
```

The live demo needs `ANTHROPIC_API_KEY`. The tests use a fake client and do not make API calls. All claim IDs, member IDs, provider IDs, service codes, policy IDs, and policy content are fictional; do not use the sample rules for real claim decisions.
