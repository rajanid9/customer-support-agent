# Claude Certification Concepts: Customer Support

This package combines a runnable customer-support agent with exam-oriented notes. The agent demonstrates tool use against a fictional electronics-store backend; `tool_demo.py` is a smaller calculator and web-search-stub exercise.

## Agentic Tool Use

- Send user messages and tool schemas with the Anthropic Messages API.
- Branch on `stop_reason`, not the wording of Claude's response: handle `tool_use`, `end_turn`, `max_tokens`, and refusal distinctly.
- Preserve the full assistant content in history so tool-use IDs remain available.
- Execute requested handlers, then return every tool result in one user message with its matching `tool_use_id`.
- Bound the loop with a maximum-turn guard; normal completion is indicated by `end_turn`.
- Use a fake client to test the orchestration offline, including sequential and same-turn multiple tool calls.

## Tool Schemas And Selection

- Give tools distinct names and descriptions that explain when to use them, required inputs, boundaries, and when not to use them.
- Use strict input schemas, required fields, enums, and `additionalProperties: false` to constrain arguments.
- Separate the schema Claude sees from the Python handler that performs the action; dispatch by tool name.
- Treat tool choice as a control: `auto` allows Claude to choose whether to call a tool, while `any` requires a tool call.
- A prompt guides selection but is not a deterministic guarantee.

## Deterministic Safety And Business Rules

- Verify a customer before reading or changing an order; verify order ownership in code.
- Enforce refund eligibility in handlers: order status, delivery window, amount limit, and duplicate-refund checks.
- Keep critical policy gates in code rather than relying only on probabilistic prompt instructions.
- Escalate customer requests, policy exceptions, and unresolved cases using clear criteria.
- Return structured errors with categories and retryability so the agent can decide whether to correct input, ask a question, retry, or escalate.

## Structured Responses And Testing

- Constrain final responses with a JSON Schema and validate them with Pydantic.
- Distinguish refusal and truncated `max_tokens` responses from successful completion.
- Test handlers and control flow with scripted fake responses instead of making API calls.
- Check tool-result IDs, policy enforcement, parallel tool results, and runaway-loop behavior.

## Calculator And Search Stub

- `tool_demo.py` demonstrates schema-to-handler dispatch for arithmetic and a deliberately unconfigured `web_search` stub.
- The calculator performs the operation in Python; the search handler explicitly reports that it does not access the internet.
- An iterative tool loop can include several model calls even for one user request.

## Additional Certification Notes

`notes.md` also covers topics beyond the runnable support agent:

- Claude Code project commands versus `CLAUDE.md` instructions, and path-scoped rules under `.claude/rules/`.
- Plan mode for large, multi-file architectural changes.
- Multi-agent task decomposition, scoped tools, and structured error propagation for recovery.
- Non-interactive Claude Code in CI with `-p`.
- When to use real-time requests versus Message Batches, considering latency requirements.
- Pull-request review as focused file-level passes followed by an integration pass.

## Product Manager Scope

You do not need to memorize the Python implementation to lead this lab. You
should be able to explain the user outcome, set acceptance criteria, and
recognize where deterministic controls are needed.

- **User outcome:** Help a customer resolve an order or product issue accurately,
  without making them repeat information or sending routine cases to a person.
- **Success criteria:** Measure correct identity and order verification,
  resolution rate, time to resolution, customer satisfaction, and escalation
  quality. Track incorrect or duplicate refunds as critical failure metrics,
  not as acceptable trade-offs for speed.
- **Boundaries:** A customer must be verified before order access or changes.
  Refund eligibility is enforced in code. Define which requests need customer
  clarification and which must be escalated to a human.
- **Quality checks:** Test normal cases, ambiguous identity, wrong order
  ownership, duplicate refunds, policy exceptions, missing information, tool
  failures, and explicit requests for a human. Review both successful and
  unsuccessful outcomes.
- **Operational trade-offs:** Agree on acceptable latency and model/tool cost,
  and require useful error reporting and a human fallback when the agent cannot
  safely proceed.

The runnable support backend is fictional. A production launch would additionally
need approved integrations, privacy/security review, auditability, and policy
owners for refund and escalation rules.
