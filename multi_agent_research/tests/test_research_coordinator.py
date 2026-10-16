"""Offline tests for planning, explicit context passing, and iterative refinement."""

from __future__ import annotations

import asyncio
import json

import pytest

from multi_agent_research.agent import (
    CoverageReview,
    DocumentAnalysis,
    ResearchPlan,
    ResearchReport,
    Source,
    Subtopic,
    WebFindings,
    run_research,
)


ENERGY_TOPICS = ["solar", "wind", "geothermal", "tidal", "biomass", "fusion"]


class ScriptedAgents:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []
        self.coverage_calls = 0
        self.web_calls = 0
        self.document_calls = 0

    async def __call__(self, role: str, prompt: str, schema: type):
        context = json.loads(prompt)
        self.calls.append((role, context))
        if schema is ResearchPlan:
            return ResearchPlan(
                subtopics=[
                    Subtopic(
                        id=name,
                        title=f"{name.title()} energy",
                        objectives=[f"Research {name} technologies"],
                    )
                    for name in ENERGY_TOPICS
                ]
            )
        if schema is WebFindings:
            self.web_calls += 1
            assigned = [item["id"] for item in context["assignments"]]
            return WebFindings(
                findings=[f"Evidence summary for {name}." for name in assigned],
                sources=[
                    Source(title=f"{name.title()} source", url=f"https://example.test/{name}", note="Test source")
                    for name in assigned
                ],
            )
        if schema is DocumentAnalysis:
            self.document_calls += 1
            assert context.get("web_research_excerpts") or context.get("new_web_research")
            return DocumentAnalysis(
                synthesis="Analyzed source notes; no user documents supplied.",
                key_findings=["Cross-technology comparison."],
            )
        if schema is CoverageReview:
            self.coverage_calls += 1
            gaps = ["fusion", "tidal"] if self.coverage_calls == 1 else []
            return CoverageReview(
                covered_subtopics=[name for name in ENERGY_TOPICS if name not in gaps],
                gap_subtopics=gaps,
                sufficient=not gaps,
                rationale="Initial pass needs deeper evidence on fusion and tidal.",
            )
        if schema is ResearchReport:
            return ResearchReport(
                topic=context["topic"],
                summary="Renewable energy technologies span established and emerging approaches.",
                subtopics=[],
                findings=[f"Evidence for {name}." for name in ENERGY_TOPICS],
                sources=[],
                coverage_complete=False,
                coverage_gaps=[],
                coverage_requirements=[],
                refinement_rounds=0,
                limitations=[],
            )
        raise AssertionError(f"Unexpected output schema: {schema}")


def test_renewable_energy_research_refines_gaps_and_covers_all_required_topics():
    agents = ScriptedAgents()
    report = asyncio.run(
        run_research(
            "Renewable energy technologies",
            documents=["A short supplied overview of energy generation."],
            call_agent=agents,
        )
    )

    assert report.coverage_complete
    assert report.coverage_gaps == []
    assert report.refinement_rounds == 1
    assert report.coverage_requirements == ENERGY_TOPICS
    for name in ENERGY_TOPICS:
        assert name in " ".join(report.subtopics).casefold()
        assert any(name in finding.casefold() for finding in report.findings)
    assert agents.web_calls == 2
    assert agents.document_calls == 2
    assert agents.coverage_calls == 2

    first_document_call = next(
        context for role, context in agents.calls
        if role == "document_analysis" and "web_research_excerpts" in context
    )
    assert first_document_call["user_supplied_documents"] == [
        "A short supplied overview of energy generation."
    ]
    assert first_document_call["web_research_excerpts"]["findings"]

    refined_web_call = [
        context for role, context in agents.calls
        if role == "web_search" and "refinement_round" in context
    ][0]
    assert {item["id"] for item in refined_web_call["assignments"]} == {"fusion", "tidal"}


def test_refinement_limit_is_reported_as_incomplete_not_success():
    agents = ScriptedAgents()
    report = asyncio.run(
        run_research(
            "Renewable energy technologies",
            call_agent=agents,
            max_refinement_rounds=0,
        )
    )
    assert report.coverage_complete is False
    assert report.refinement_rounds == 0
    assert report.coverage_gaps == ["fusion", "tidal"]


def test_empty_topic_is_rejected_before_agent_calls():
    agents = ScriptedAgents()
    with pytest.raises(ValueError, match="topic must not be empty"):
        asyncio.run(run_research("  ", call_agent=agents))
    assert agents.calls == []
