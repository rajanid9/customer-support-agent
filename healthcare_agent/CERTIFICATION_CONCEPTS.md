# Claude Certification Concepts: Healthcare Claims

This package demonstrates an agentic loop over fictional claims and edit records. The data and workflow guides are synthetic examples, not real clinical, coverage, or adjudication policy.

## Data And Rule Mapping

- Represent claims, provider records, and fired edits as structured JSON.
- Link claims to providers by `provider_id` and edits to Markdown workflow guides by an allowlisted `rule_key`.
- Keep human-readable workflow guidance separate from tool code and mock records.
- Use project-relative asset paths so the agent can load JSON and rule files after the package is moved.

## Tool Contracts And Deterministic Work

- Define strict tool schemas with clear descriptions and constrained inputs.
- Use tools to retrieve claims/providers, read edit guidance, summarize provider-level edit frequencies, and queue mock follow-up actions.
- Calculate counts and claim IDs in Python rather than asking the model to estimate them.
- Validate that an edit belongs to the claim and that a documentation request is allowed by its disposition.
- Return structured success/error tool results and match each result to its `tool_use_id`.

## Agentic Loop

- Start with `tool_choice: any` for the first tool call; use `auto` on later turns so Claude can continue with tools or finish.
- On `tool_use`, execute the handler and send tool results back; on `end_turn`, return the final text.
- Allow independent lookups to be requested in the same turn; a final answer may require multiple tool-use rounds.
- Use a turn limit as a runaway-loop safeguard, not as the normal completion signal.
- Test tool orchestration with a fake client, including final-text termination without an extra API call.

## Human Review And Safety Boundaries

- Never infer medical necessity or coverage, or approve, deny, or modify a claim.
- Route unresolved policy/configuration questions to human review.
- Queue documentation and review requests only as in-memory mock actions; they do not contact providers or persist data.
- Clearly label all records, edit guidance, and actions as synthetic.

## Notebook Learning Workflow

`healthcare_agentic_loop.ipynb` separates deterministic Python analysis from model behavior:

1. Load and inspect the claims and provider data.
2. Read a rule guide using an edit's `rule_key`.
3. Count provider edit frequencies directly in Python.
4. Compare those counts with the agent's summary handler.
5. Read each applicable guide and optionally invoke the live model loop.

The live cell requires `ANTHROPIC_API_KEY`; the notebook uses hidden input rather than storing the key in a cell. Offline tests use a fake client and need no API key.
