# Multi-Agent Research: Certification and Product Manager Test Prep

Use these questions to review the hub-and-spoke research lab and practice
explaining design decisions from both a certification and product-management
perspective. Answers below summarize the learner's responses, with feedback to
make the concepts precise.

## Certification Questions

### 1. How do the prompt and `allowed_tools` work together?

**Question:** The Web Search specialist's prompt tells it to use `WebSearch`,
and `_sdk_call()` includes `WebSearch` and `WebFetch` in `allowed_tools`. What
does each part do?

**Learner's answer:** The prompt guides the model on how to use tools, so both
the role and allowed tools are important.

**Feedback:** Correct. The prompt describes the role, task, and intended tool
use. The SDK configuration makes the listed tools available to that call. A
prompt cannot enable a tool that is not allowed, and an allowed tool is not
necessarily used unless the model decides it is relevant.

### 2. What belongs in the acceptance criteria when a topic area is missing?

**Question:** A report covers solar, wind, geothermal, biomass, and fusion but
omits tidal. What should the acceptance criterion require, and what should
happen if refinement still does not cover tidal?

**Learner's answer:** Check the coverage report to ensure every in-scope area is
covered, and ensure the coordinator decomposes the topic broadly enough.

**Feedback:** Good. Make the requirement measurable: for this benchmark, the
final report must address solar, wind, geothermal, tidal, biomass, and fusion.
The plan itself should also be inspected for breadth. If refinement still
misses tidal, the report must be marked incomplete and show tidal as a gap.

### 3. What context should be passed to Document Analysis?

**Question:** Document Analysis has no search tools. What must the coordinator
pass to it, and why?

**Learner's answer:** Subagents do not inherit the coordinator's or other
subagents' conversation history, so the coordinator must explicitly pass
context, including Web Search results.

**Feedback:** Correct. Pass the topic, subtopic objectives, user-provided
documents, and Web Search findings. On refinement, pass the relevant prior
analysis and the reason those subtopics were identified as gaps.

### 4. Is breadth enough to establish source quality?

**Question:** The report covers all six technologies, but some findings use
weak or outdated sources. Is coverage alone enough?

**Learner's answer:** Ensure each subagent researches with enough breadth and
detail.

**Feedback:** Breadth and detail are necessary but do not establish trust.
Define source standards too: credible sources for important claims, preference
for current material, traceable links, and visible uncertainty or conflicting
evidence.

### 5. When should iterative research stop?

**Question:** More sources and refinement can improve coverage but increase
latency and cost. How should the coordinator decide to stop?

**Learner's answer:** Use measurable coverage criteria; once the report meets
the required scope, stop delegating and return it.

**Feedback:** Correct. Pair the coverage threshold with a maximum number of
rounds or a cost/latency budget. If the limit is reached before coverage is
sufficient, return an explicitly incomplete report with remaining gaps.

### 6. What should a timed-out Web Search specialist report?

**Question:** Web Search times out after finding two useful sources. What
information should go back to the coordinator?

**Learner's answer:** The partial results and the timeout, so the coordinator
can decide whether to retry or delegate differently.

**Feedback:** Correct. Include the failure type, attempted queries, partial
findings and their sources, and a useful retry or alternative suggestion.
Structured error context lets the coordinator recover intelligently.

### 7. Why should tools be scoped by specialist role?

**Question:** Why does Document Analysis have no web tools while Web Search
does? What can go wrong if every specialist gets every tool?

**Learner's answer:** Document Analysis synthesizes supplied material and does
not need web tools. Giving every agent tools may increase latency.

**Feedback:** Right. Broad tool access can cause duplicate or unnecessary
calls, raising cost and latency. It can also blur responsibilities and make
research less traceable. Scope each specialist to the tools needed for its
assigned job.

### 8. Why use structured outputs?

**Question:** Why use models such as `WebFindings` and `CoverageReview` rather
than free-form text?

**Learner's answer:** Structured output makes the final response easier for
downstream consumers.

**Feedback:** Correct. It also makes validation, gap comparison, aggregation,
and routing deterministic for the coordinator, without fragile prose parsing.

### 9. Why bound the refinement loop?

**Question:** Why limit refinement rounds, and what should happen if coverage
is still incomplete?

**Learner's answer:** A bounded loop prevents an infinite loop and controls
cost. The coordinator can refine assignments or decomposition when gaps remain.

**Feedback:** Correct. Refine within the configured limit. Once exhausted,
stop, identify the remaining gaps, and mark the report incomplete instead of
claiming success.

## Product Manager Questions

### 10. What should the acceptance criteria say about coverage?

**Question:** How should the PM decide whether the renewable-energy report
meets its scope?

**Learner's answer:** Define scope coverage and verify that the coordinator
decomposes the topic across all relevant areas.

**Feedback:** Turn this into testable criteria: require findings for solar,
wind, geothermal, tidal, biomass, and fusion, and verify that the final report
explicitly exposes any omissions. Fusion should be distinguished as an
emerging technology, not a currently deployed renewable source.

### 11. What evidence is needed for high-impact decision support?

**Question:** What should be required before users rely on a report for a
high-impact decision, especially when sources conflict or coverage is
incomplete?

**Learner's answer:** Require explainability and evidence for each research
finding, and enough coverage for the decision-support need.

**Feedback:** Good. Require traceable sources for key claims, visible
uncertainty and conflicts, and a clear statement when the report is incomplete.
For high-impact use, route unresolved evidence or coverage gaps to human review.

### 12. Which metrics indicate product success?

**Question:** What metrics would show whether the coordinator is useful and
reliable? Include quality and operational measures.

**Learner's answer:** Quality: coverage reports meet success criteria.
Operational: the coordinator decomposes the topic to include all in-scope
areas.

**Feedback:** Both are useful quality measures. Add operational measures such
as end-to-end report latency, cost per report, and specialist/tool failure
rate. Separately track source quality and unsupported claims.

## Practice Question (Not Yet Answered)

### 13. What should be validated before launch?

Name one research-quality check and one operational-readiness check you would
require before releasing the coordinator to users. Consider live search
accuracy, source standards, failure monitoring, latency/cost budgets, and
human review for high-impact topics.

## Product Manager Takeaway

A PM does not need to memorize the implementation. The important skills are
setting observable success criteria, defining boundaries and failure behavior,
checking source quality and coverage, and balancing user value against latency,
cost, and operational risk. Understanding the role of prompts, tool
permissions, structured handoffs, and refinement helps the PM review the
system and work effectively with engineering.

## Personal Reflection: What to Strengthen Next

### What is already clear

- Prompts guide agent behavior, while tool permissions determine which tools a
  specialist can use.
- Subagents need explicit context from the coordinator; they should not be
  assumed to inherit another agent's conversation history.
- Coverage gaps should trigger bounded refinement, and unresolved gaps should
  be reported honestly instead of being presented as success.

### Skills to practice

1. **Make acceptance criteria measurable.** Instead of “cover every area,”
   specify that each required topic needs a relevant finding and traceable
   source. If any are missing, the report must identify the gap and be marked
   incomplete.
2. **Separate quality from operational metrics.** Coverage, decomposition,
   source quality, and unsupported-claim rate measure answer quality. Latency,
   cost per report, and tool failure rate measure operational performance.
3. **Define source-quality standards.** Specify expectations for source
   credibility, freshness, evidence links, and how to disclose conflicting or
   uncertain evidence.
4. **Specify recovery context.** On failure, return the failure type, attempted
   query, partial findings and sources, and a suggested next step so the
   coordinator can choose whether to retry, delegate differently, or report a
   gap.
5. **Connect system limits to user experience.** Set a refinement-round or
   budget limit, then state what users see when that limit is reached:
   incomplete status, remaining gaps, and any human-review recommendation.

### Reflection exercise

Write a one-page acceptance checklist for a research workflow. Include:

- Required topic coverage and what evidence counts for each topic.
- Source quality and freshness expectations.
- How uncertainty, conflicting evidence, and missing sources are reported.
- Behavior after a tool failure and after refinement is exhausted.
- Maximum refinement rounds, latency target, and cost budget.
- A test or metric that verifies each requirement.

After drafting the checklist, ask: **Could an engineer turn each requirement
into a test or metric, and would a user know when the report is not ready to
support a decision?**

## Sample Acceptance Criteria Checklist

Use this as a starting point for the renewable-energy research lab. Adjust the
thresholds and standards with subject-matter experts before using the system
for real decisions.

### Scope and coverage

- [ ] The plan has at least five distinct subtopics and represents the breadth
  of the user's topic.
- [ ] For the renewable-energy benchmark, the final report addresses solar,
  wind, geothermal, tidal, biomass, and fusion.
- [ ] Each required area has at least one relevant finding and a source that
  supports that finding; merely naming a topic does not count as coverage.
- [ ] Fusion is identified as an emerging technology, not a currently deployed
  renewable source.
- [ ] If a required area is unsupported after the refinement limit, the report
  is marked incomplete and names every remaining gap.

### Evidence and quality

- [ ] Key factual findings include source titles and working URLs.
- [ ] Sources meet an agreed credibility and recency standard for the domain.
- [ ] Important claims can be traced to the source supporting them.
- [ ] Uncertainty, conflicting evidence, and limitations are disclosed.
- [ ] The system does not invent sources, citations, or document contents.

### Orchestration and recovery

- [ ] Each specialist receives the topic, assigned subtopics, objectives, and
  the relevant prior results needed for its task.
- [ ] Document Analysis receives user-provided documents and Web Search
  findings as explicit context.
- [ ] A coverage gap triggers another targeted delegation within the configured
  round limit.
- [ ] Search failures return the failure type, attempted query, partial
  findings/sources, and a useful recovery signal when available.
- [ ] The workflow stops at the configured refinement limit and does not
  describe an incomplete report as complete.

### Operational readiness

- [ ] Define a target maximum end-to-end latency for a typical research task.
- [ ] Define an acceptable maximum API/search cost per report.
- [ ] Track model/tool errors, retries, incomplete reports, and coverage gaps.
- [ ] Define when high-impact findings require human review before use.
- [ ] Confirm credentials are handled securely and never included in prompts,
  reports, logs, or version control.

### Evaluation plan

- [ ] Maintain representative test topics, including broad topics and
  deliberately difficult or ambiguous requests.
- [ ] Test omitted subtopics, weak or conflicting evidence, tool timeout,
  malformed structured results, and refinement exhaustion.
- [ ] Run deterministic offline tests for orchestration and context passing.
- [ ] Separately evaluate live research for source quality and factual
  accuracy; passing offline orchestration tests is not evidence of factual
  correctness.
- [ ] Review results with subject-matter experts and revise the criteria when
  the intended decision or user need changes.

## Recommended Learning Resources

These official Claude/Anthropic resources align with the topics above. Start
with evaluation and success criteria, then study the SDK and agent behavior.

1. [Define success criteria and build evaluations](https://platform.claude.com/docs/en/test-and-evaluate/develop-tests) —
   turn product goals into measurable checks and evaluations.
2. [Prompt engineering overview](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/overview) —
   understand when prompt changes help and why evaluation should come first.
3. [Prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices) —
   improve instructions, examples, tool guidance, and agent prompts.
4. [Claude Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview)
   and [Quickstart](https://code.claude.com/docs/en/agent-sdk/quickstart) —
   understand SDK capabilities, configuration, and execution.
5. [Subagents in the SDK](https://code.claude.com/docs/en/agent-sdk/subagents) —
   learn the SDK's named subagent feature. This lab currently makes separate
   SDK calls per role from Python rather than using SDK-managed subagent
   spawning.
6. [Tool use with Claude](https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview) —
   distinguish tool instructions in prompts from tool availability and
   execution configuration.
7. [Structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) —
   learn how schema-constrained outputs help downstream validation and
   orchestration.
8. [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents) —
   consider workflow-versus-agent design and trade-offs in complexity,
   performance, latency, and cost. Treat it as architectural perspective and
   pair it with current SDK documentation.
