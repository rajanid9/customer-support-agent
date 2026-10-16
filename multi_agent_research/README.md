# Multi-Agent Research Coordinator Lab

Build a **hub-and-spoke research coordinator**: the coordinator plans and
checks coverage; the Web Search and Document Analysis specialists do bounded
work and report back. The coordinator combines their results and delegates
coverage gaps for another pass.

This lab uses the Claude Agent SDK. The offline tests use scripted agents, so
you can learn and verify the orchestration without credentials or live search.
The live Web Search specialist requires Claude Code/Agent SDK access to the
built-in `WebSearch` and `WebFetch` tools. The SDK is configured with its
`sonnet` model alias, so the runtime resolves a Sonnet model available to your
account rather than requiring a hard-coded model identifier.

## Step 1 — Inspect the contracts

Open [`agent.py`](./agent.py). Each Pydantic model defines a structured
handoff: `ResearchPlan`, `WebFindings`, `DocumentAnalysis`, `CoverageReview`,
and `ResearchReport`. Structured handoffs make it possible to validate agent
outputs and test the workflow without relying on prose parsing.

For certification and product-manager practice, see
[`TEST_PREP.md`](./TEST_PREP.md).

For renewable-energy topics, the coordinator has six required breadth checks:
solar, wind, geothermal, tidal, biomass, and fusion. Fusion is included because
the exercise explicitly asks for it; the final report should distinguish it
from currently deployed renewable technologies.

## Step 2 — Plan before researching

`run_research()` first asks the coordinator for at least five distinct
subtopics. It checks this minimum in Python. For renewable energy it also adds
any missing required technology areas, so a narrow model-generated plan cannot
silently omit one of the exercise's required areas.

## Step 3 — Pass task context to the Web Search spoke

The Web Search specialist receives the broad topic plus every planned
subtopic's id, title, and research objectives. During refinement, it receives
only the uncovered assignments, previous findings, and the evaluator's reason
for requesting more research. Its live SDK configuration enables `WebSearch`
and `WebFetch`.

## Step 4 — Pass source context to the Document Analysis spoke

The Document Analysis specialist receives the same subtopic assignments,
user-supplied document text, and the Web Search findings as source excerpts.
The prompt explicitly prohibits inventing documents or citations. Without
user-supplied documents, it must say that it analyzed source notes rather than
pretending to have read full papers.

## Step 5 — Aggregate and evaluate coverage

The coordinator sends the plan, web findings, and document analysis to the
coverage evaluator. Coverage is complete only when the evaluator marks the
work sufficient **and** no planned subtopic remains uncovered. Unknown gap ids
are rejected rather than silently ignored.

## Step 6 — Refine gaps, with a limit

If coverage is insufficient, the coordinator re-delegates only the identified
gaps to both specialists and evaluates again. The default allows two
refinement rounds. If gaps remain when the limit is reached, the report is
explicitly marked incomplete; the workflow does not turn an exhausted retry
into a success-shaped result.

## Step 7 — Run the offline renewable-energy exercise

From the repository root:

```bash
./.venv/bin/python -m pytest multi_agent_research/tests/test_research_coordinator.py -q
```

The scripted test deliberately leaves tidal and fusion weakly covered on the
first pass, verifies that those assignments are sent back to both specialists,
then confirms a complete report covering solar, wind, geothermal, tidal,
biomass, and fusion. It also checks that document text and web findings are
actually passed into the document-analysis prompt.

## Step 8 — Run live research

Set `ANTHROPIC_API_KEY` in your shell, then start the coordinator. In zsh, you
can enter the key without echoing it:

```bash
read -s "ANTHROPIC_API_KEY?Paste your API key (input hidden): "
export ANTHROPIC_API_KEY
echo
./.venv/bin/python -m multi_agent_research.agent "Renewable energy technologies"
```

You can pass documents directly in Python:

```python
import asyncio
from multi_agent_research.agent import run_research

report = asyncio.run(
    run_research(
        "Renewable energy technologies",
        documents=["Paste a report excerpt or document text here."],
    )
)
print(report.model_dump_json(indent=2))
```

The live result depends on model and search-tool availability. The offline test
verifies orchestration and required output coverage, not the accuracy of live
web sources.

## Product Manager Scope

You do not need to memorize the Python implementation to lead this lab. You
should be able to explain the research outcome, define what complete coverage
means, and understand when the system must report uncertainty instead of
claiming success.

- **User outcome:** Deliver a useful, source-backed overview of a broad topic
  without silently omitting important areas.
- **Success criteria:** For the renewable-energy benchmark, verify coverage of
  solar, wind, geothermal, tidal, biomass, and fusion. Also evaluate source
  quality, factual support, clarity of caveats, and whether remaining gaps are
  visible in the final report. Fusion must be described as emerging rather than
  a currently deployed renewable source.
- **Boundaries:** Distinguish sourced facts from uncertainty. Do not invent
  citations or pretend that source excerpts are full documents. If coverage is
  inadequate after the refinement limit, report an incomplete result with its
  gaps.
- **Quality checks:** Test broad versus narrow topics, missing subtopics,
  unsupported findings, weak sources, failed search, invalid gap identifiers,
  and exhaustion of refinement rounds. The offline tests check orchestration
  and context passing; they do not prove live research accuracy.
- **Operational trade-offs:** Set acceptable latency, API/search cost, source
  freshness, and number of refinement rounds. Consider when a human researcher
  should review high-impact conclusions.

Before production use, define source-quality standards, evaluation datasets,
monitoring, and review requirements appropriate to the research domain.
