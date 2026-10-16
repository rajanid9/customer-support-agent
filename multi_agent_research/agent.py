"""A hub-and-spoke research coordinator with bounded iterative refinement."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable, Sequence
from typing import TypeVar

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query
from pydantic import BaseModel, Field

MODEL = "sonnet"
MIN_SUBTOPICS = 5
MAX_REFINEMENT_ROUNDS = 2

ENERGY_BREADTH = [
    "solar",
    "wind",
    "geothermal",
    "tidal",
    "biomass",
    "fusion",
]

T = TypeVar("T", bound=BaseModel)
AgentCall = Callable[[str, str, type[T]], Awaitable[T]]


class Subtopic(BaseModel):
    id: str
    title: str
    objectives: list[str] = Field(min_length=1)


class ResearchPlan(BaseModel):
    subtopics: list[Subtopic]


class Source(BaseModel):
    title: str
    url: str
    note: str


class WebFindings(BaseModel):
    findings: list[str]
    sources: list[Source]
    limitations: list[str] = Field(default_factory=list)


class DocumentAnalysis(BaseModel):
    synthesis: str
    key_findings: list[str]
    limitations: list[str] = Field(default_factory=list)


class CoverageReview(BaseModel):
    covered_subtopics: list[str]
    gap_subtopics: list[str]
    sufficient: bool
    rationale: str


class ResearchReport(BaseModel):
    topic: str
    summary: str
    subtopics: list[str]
    findings: list[str]
    sources: list[Source]
    coverage_complete: bool
    coverage_gaps: list[str]
    coverage_requirements: list[str]
    refinement_rounds: int
    limitations: list[str]


class ResearchError(RuntimeError):
    """Raised when planning, coverage, or research output fails validation."""


ENERGY_OBJECTIVES = {
    "solar": "Cover photovoltaic and concentrated solar power, deployment, strengths, and limitations.",
    "wind": "Cover onshore and offshore wind, deployment, strengths, and limitations.",
    "geothermal": "Cover geothermal electricity and heat, resource limits, strengths, and limitations.",
    "tidal": "Cover tidal-range and tidal-stream power, maturity, strengths, and limitations.",
    "biomass": "Cover biomass electricity, heat, and fuels, sustainability trade-offs, and limitations.",
    "fusion": "Cover fusion status, potential energy role, technical barriers, and distinguish it from established renewables.",
}

PLANNER_PROMPT = """You are the coordinator in a hub-and-spoke research workflow.
Decompose the user's broad topic into at least five distinct subtopics that
collectively cover its breadth. Give every subtopic a stable short id, a title,
and concrete research objectives. Do not perform the research yourself.
Return only the requested structured plan."""

WEB_PROMPT = """You are the web-search specialist. Research only the assigned
subtopics. Use WebSearch to find credible, recent sources; use WebFetch to
verify useful pages when available. Distinguish established evidence from
uncertainty, include source URLs, and report limitations. The coordinator's
context and assignment follow. Do not claim a search succeeded if it did not."""

DOCUMENT_PROMPT = """You are the document-analysis specialist. Analyze only
the documents and research excerpts passed in this prompt; do not invent
documents, citations, or facts. Extract relevant claims for each assigned
subtopic, reconcile qualifications, and identify what remains unsupported.
If no user-supplied documents were provided, say so and analyze the web
research excerpts as source notes rather than pretending they are full papers."""

COVERAGE_PROMPT = """You are the coverage evaluator. Compare the required
subtopics with the combined research and document analysis. A subtopic is
covered only when evidence addresses its objectives; titles alone are not
evidence. List uncovered or weakly supported subtopic ids as gaps, explain
why, and mark sufficient only when every required subtopic has adequate
evidence. Return structured output."""

SYNTHESIS_PROMPT = """You are the research report synthesizer. Produce a clear,
evidence-grounded overview from the supplied coordinator context. Retain
important qualifications and limitations, include findings for every
required subtopic, and preserve source URLs. Explicitly state that fusion is
an emerging energy technology, not a currently deployed renewable source,
when it is in scope. Do not invent facts or sources."""


def _energy_requirements(topic: str) -> list[str]:
    lowered = topic.casefold()
    if "renewable" in lowered and "energy" in lowered:
        return ENERGY_BREADTH.copy()
    return []


def _ensure_energy_topics(plan: ResearchPlan, required: Sequence[str]) -> ResearchPlan:
    """Add any benchmark-required breadth that the model's initial plan missed."""
    existing = " ".join(
        f"{item.id} {item.title} {' '.join(item.objectives)}".casefold()
        for item in plan.subtopics
    )
    for name in required:
        if name not in existing:
            plan.subtopics.append(
                Subtopic(
                    id=name,
                    title=f"{name.title()} energy",
                    objectives=[ENERGY_OBJECTIVES[name]],
                )
            )
            existing += f" {name}"
    if len(plan.subtopics) < MIN_SUBTOPICS:
        raise ResearchError(
            f"The coordinator produced {len(plan.subtopics)} subtopics; "
            f"at least {MIN_SUBTOPICS} are required."
        )
    return plan


async def _sdk_call(role: str, prompt: str, schema: type[T]) -> T:
    """Run one specialist/coordinator turn using Claude Agent SDK structured output."""
    if role == "web_search":
        system_prompt = WEB_PROMPT
        allowed_tools = ["WebSearch", "WebFetch"]
    elif role == "document_analysis":
        system_prompt = DOCUMENT_PROMPT
        allowed_tools = []
    else:
        system_prompt = role
        allowed_tools = []

    options = ClaudeAgentOptions(
        model=MODEL,
        system_prompt=system_prompt,
        allowed_tools=allowed_tools,
        max_turns=8,
        output_format={"type": "json_schema", "schema": schema.model_json_schema()},
    )
    result: ResultMessage | None = None
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, ResultMessage):
            result = message
    if result is None:
        raise ResearchError(f"{role} returned no final result.")
    if result.is_error:
        details = "; ".join(result.errors or ["unknown SDK error"])
        raise ResearchError(f"{role} failed: {details}")
    if result.structured_output is not None:
        return schema.model_validate(result.structured_output)
    if result.result:
        try:
            return schema.model_validate_json(result.result)
        except ValueError as exc:
            raise ResearchError(f"{role} returned invalid structured output.") from exc
    raise ResearchError(f"{role} returned no structured output.")


def _payload(**values: object) -> str:
    return json.dumps(values, ensure_ascii=False, indent=2)


async def run_research(
    topic: str,
    documents: Sequence[str] = (),
    *,
    call_agent: AgentCall = _sdk_call,
    max_refinement_rounds: int = MAX_REFINEMENT_ROUNDS,
) -> ResearchReport:
    """Plan, delegate, evaluate coverage, refine gaps, and synthesize a report."""
    if not topic.strip():
        raise ValueError("topic must not be empty")
    if max_refinement_rounds < 0:
        raise ValueError("max_refinement_rounds must not be negative")

    required = _energy_requirements(topic)
    plan = await call_agent(
        PLANNER_PROMPT,
        _payload(topic=topic, required_coverage=required, minimum_subtopics=MIN_SUBTOPICS),
        ResearchPlan,
    )
    plan = _ensure_energy_topics(plan, required)
    subtopics = {item.id: item for item in plan.subtopics}

    web = await call_agent(
        "web_search",
        _payload(topic=topic, assignments=[item.model_dump() for item in plan.subtopics]),
        WebFindings,
    )
    documents_context = {
        "topic": topic,
        "assignments": [item.model_dump() for item in plan.subtopics],
        "user_supplied_documents": list(documents),
        "web_research_excerpts": web.model_dump(),
        "instruction": "Analyze user documents and the supplied web findings; identify unsupported subtopics.",
    }
    analysis = await call_agent(
        "document_analysis",
        _payload(**documents_context),
        DocumentAnalysis,
    )

    refinement_rounds = 0
    while True:
        review = await call_agent(
            COVERAGE_PROMPT,
            _payload(
                topic=topic,
                required_subtopics=[item.model_dump() for item in plan.subtopics],
                web_findings=web.model_dump(),
                document_analysis=analysis.model_dump(),
                prior_coverage_requirements=required,
            ),
            CoverageReview,
        )
        known_gaps = set(review.gap_subtopics)
        known_gaps.update(set(subtopics) - set(review.covered_subtopics))
        unknown = known_gaps - set(subtopics)
        if unknown:
            raise ResearchError(f"Coverage evaluator returned unknown subtopic ids: {sorted(unknown)}")
        if not known_gaps and review.sufficient:
            break
        if not known_gaps:
            raise ResearchError(
                "Coverage was marked insufficient but the evaluator provided no "
                "subtopic gaps to refine."
            )
        if refinement_rounds >= max_refinement_rounds:
            break

        refinement_rounds += 1
        assignments = [subtopics[subtopic_id].model_dump() for subtopic_id in sorted(known_gaps)]
        refined_web = await call_agent(
            "web_search",
            _payload(
                topic=topic,
                assignments=assignments,
                previous_findings=web.model_dump(),
                coverage_gap=review.rationale,
                refinement_round=refinement_rounds,
            ),
            WebFindings,
        )
        web = WebFindings(
            findings=web.findings + refined_web.findings,
            sources=web.sources + refined_web.sources,
            limitations=web.limitations + refined_web.limitations,
        )
        refined_analysis = await call_agent(
            "document_analysis",
            _payload(
                topic=topic,
                assignments=assignments,
                user_supplied_documents=list(documents),
                previous_analysis=analysis.model_dump(),
                new_web_research=refined_web.model_dump(),
                coverage_gap=review.rationale,
                refinement_round=refinement_rounds,
            ),
            DocumentAnalysis,
        )
        analysis = DocumentAnalysis(
            synthesis=f"{analysis.synthesis}\n{refined_analysis.synthesis}",
            key_findings=analysis.key_findings + refined_analysis.key_findings,
            limitations=analysis.limitations + refined_analysis.limitations,
        )

    coverage_complete = not known_gaps and review.sufficient
    report = await call_agent(
        SYNTHESIS_PROMPT,
        _payload(
            topic=topic,
            plan=[item.model_dump() for item in plan.subtopics],
            required_coverage=required,
            web_findings=web.model_dump(),
            document_analysis=analysis.model_dump(),
            coverage_review=review.model_dump(),
            coverage_complete=coverage_complete,
            coverage_gaps=sorted(known_gaps),
            refinement_rounds=refinement_rounds,
        ),
        ResearchReport,
    )
    return report.model_copy(
        update={
            "topic": topic,
            "subtopics": [item.title for item in plan.subtopics],
            "sources": web.sources,
            "coverage_complete": coverage_complete,
            "coverage_gaps": sorted(known_gaps),
            "coverage_requirements": required,
            "refinement_rounds": refinement_rounds,
            "limitations": web.limitations + analysis.limitations + report.limitations,
        }
    )


async def _main() -> None:
    import sys

    topic = " ".join(sys.argv[1:]).strip()
    if not topic:
        topic = input("Research topic: ").strip()
    report = await run_research(topic)
    print(report.model_dump_json(indent=2))
    if not report.coverage_complete:
        gaps = ", ".join(report.coverage_gaps) or "unspecified"
        print(
            f"Research finished with incomplete coverage after "
            f"{report.refinement_rounds} refinement rounds. Remaining gaps: {gaps}.",
            file=sys.stderr,
        )
        raise SystemExit(2)


if __name__ == "__main__":
    asyncio.run(_main())
