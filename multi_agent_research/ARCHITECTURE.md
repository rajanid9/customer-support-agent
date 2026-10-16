# Multi-Agent Research: Configuration and SDK Flow

This note explains how the research lab configures its coordinator and
specialists, passes context between them, and calls the Claude Agent SDK.
The implementation is in [`agent.py`](./agent.py).

## The hub-and-spoke design

`run_research()` is the **hub**. It owns the workflow and state:

1. Ask the planner for a structured research plan.
2. Pass the plan to the Web Search specialist.
3. Pass the plan, user documents, and web findings to Document Analysis.
4. Ask the coverage evaluator whether every subtopic has adequate evidence.
5. If there are gaps, delegate those subtopics for another research/analysis
   pass, within a configured round limit.
6. Ask for a final report and combine it with validated state from the hub.

The specialists are **spokes**: they perform bounded tasks and return results
to the hub. They do not independently decide the overall workflow.

## Where the roles are configured

The prompt constants describe the behavior expected from each role:

- `PLANNER_PROMPT` asks for a broad plan with at least five subtopics.
- `WEB_PROMPT` asks for source-backed research on assigned subtopics.
- `DOCUMENT_PROMPT` limits analysis to provided documents and research excerpts.
- `COVERAGE_PROMPT` checks evidence against the planned objectives and finds gaps.
- `SYNTHESIS_PROMPT` asks for the final evidence-grounded report.

The structured Pydantic models define what each role returns:
`ResearchPlan`, `WebFindings`, `DocumentAnalysis`, `CoverageReview`, and
`ResearchReport`. This lets the program validate and route outputs without
trying to parse arbitrary prose.

## How `_sdk_call()` connects a role to the SDK

`_sdk_call(role, prompt, schema)` is the common adapter around the SDK. It
selects the system prompt and tool allowlist for a specialist:

```python
if role == "web_search":
    system_prompt = WEB_PROMPT
    allowed_tools = ["WebSearch", "WebFetch"]
elif role == "document_analysis":
    system_prompt = DOCUMENT_PROMPT
    allowed_tools = []
else:
    system_prompt = role
    allowed_tools = []
```

It then configures and runs the SDK:

```python
options = ClaudeAgentOptions(
    model=MODEL,
    system_prompt=system_prompt,
    allowed_tools=allowed_tools,
    max_turns=8,
    output_format={"type": "json_schema", "schema": schema.model_json_schema()},
)

async for message in query(prompt=prompt, options=options):
    ...
```

In this configuration:

- `MODEL` is set to the SDK's `"sonnet"` alias so the runtime resolves a Sonnet
  model available to the authenticated account.
- `system_prompt` sets the role's instructions.
- `allowed_tools` grants the Web Search specialist access to search/fetch
  tools. The prompt encourages tool use, but does not enable tools by itself.
- `prompt` contains the current assignment and all context passed by the hub.
- `output_format` asks the SDK/model for data matching the requested Pydantic
  schema.
- `max_turns` limits the work in this SDK call; it is separate from the
  coordinator's refinement-round limit.

The model decides whether to request an allowed tool. The SDK/runtime handles
the tool invocation and returns the result to the model. Document Analysis has
an empty tool allowlist, so it works only from information supplied in its
prompt. Built-in tool availability depends on the Agent SDK/Claude Code
runtime and its configuration.

When the SDK finishes, `_sdk_call()` checks for a final `ResultMessage`,
surfaces SDK errors, and validates structured output against `schema`. It
raises `ResearchError` if no usable structured result is returned.

## How the hub passes context

Each call to `call_agent` includes three parts:

```python
await call_agent(role, prompt_text, OutputModel)
```

`role` selects specialist configuration, `prompt_text` contains the specific
task and context, and `OutputModel` is the expected output type. The default
`call_agent` is `_sdk_call`; tests inject a scripted callable instead.

### Initial Web Search assignment

The hub passes the topic and all plan entries (id, title, and objectives) as
JSON. The specialist is told to research only those assigned areas.

### Initial Document Analysis assignment

The hub passes the plan, user-provided document text, and the complete
`WebFindings` output. The prompt clarifies that web findings are source notes,
not full documents, unless actual document text was supplied.

### Coverage evaluation

The evaluator receives the plan, web findings, document analysis, and any
required topic-specific coverage checks. It returns covered ids, gap ids, a
sufficiency decision, and a rationale.

### Refinement

If gaps remain, the hub sends only those subtopics to Web Search, along with
prior web findings and the evaluator's rationale. It then sends the new web
findings, relevant documents, and prior analysis to Document Analysis. The hub
merges the new findings with the existing results before reevaluating coverage.

## Coverage safeguards

- The plan must have at least `MIN_SUBTOPICS` entries.
- Renewable-energy topics must include solar, wind, geothermal, tidal,
  biomass, and fusion; missing areas are added as explicit assignments.
- Coverage is complete only when the evaluator says `sufficient` and no
  planned subtopic remains uncovered.
- Unknown gap ids are treated as an error.
- Refinement stops at `MAX_REFINEMENT_ROUNDS`. Remaining gaps are reported in
  `coverage_gaps`, and `coverage_complete` remains false.
- A coverage response that says insufficient but provides no gaps is rejected,
  since the hub cannot sensibly delegate a refinement task without a target.

Fusion is required for the lab benchmark, but the synthesis instructions ask
the report to distinguish it as an emerging technology rather than a
currently deployed renewable energy source.

## Test the orchestration without live SDK calls

`tests/test_research_coordinator.py` supplies a scripted `call_agent`. That
lets the tests verify the workflow and exact context passing without API
credentials or search. The renewable-energy test makes the first coverage
review identify tidal and fusion as gaps, then verifies that just those gaps
are sent for refinement and that the successful second review produces a
complete report.

Run from the repository root:

```bash
./.venv/bin/python -m pytest multi_agent_research/tests/test_research_coordinator.py -q
```

## Run with the live SDK

Set `ANTHROPIC_API_KEY` in the environment and run:

```bash
./.venv/bin/python -m multi_agent_research.agent "Renewable energy technologies"
```

The CLI renders a readable Markdown-style report by default. Add `--json`
before the topic to print structured JSON instead.

Live results require valid SDK credentials and runtime access to the configured
built-in web tools. Offline tests establish that the orchestration and coverage
checks work; they do not verify live search accuracy or source availability.
