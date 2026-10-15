"""Agentic-loop demo for synthetic clinical-policy claim edits."""

import json
import uuid
from collections import Counter
from pathlib import Path

import anthropic

ASSET_DIR = Path(__file__).resolve().parent
MODEL = "claude-opus-5"
MAX_TURNS = 10

with (ASSET_DIR / "claims.json").open(encoding="utf-8") as file:
    CLAIMS = json.load(file)["claims"]
with (ASSET_DIR / "providers.json").open(encoding="utf-8") as file:
    PROVIDERS = json.load(file)["providers"]

CLAIMS_BY_ID = {claim["claim_id"]: claim for claim in CLAIMS}
PROVIDERS_BY_ID = {provider["provider_id"]: provider for provider in PROVIDERS}
RULE_FILES = {
    "authorization": "authorization.md",
    "documentation": "documentation.md",
    "utilization": "utilization.md",
    "coding_provider": "coding_provider.md",
    "coverage_demographics": "coverage_demographics.md",
}

REVIEW_TASKS = []
DOCUMENTATION_REQUESTS = []

TOOLS = [
    {
        "name": "summarize_provider_edits",
        "description": (
            "For a provider, scan all synthetic claims and count fired edit categories "
            "and rule keys. Use this for questions about the most frequent edits; "
            "then read each returned rule_key with get_edit_policy."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {"provider_id": {"type": "string"}},
            "required": ["provider_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_claim",
        "description": "Retrieve one synthetic claim and its fired edits. Use before discussing a claim.",
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {"claim_id": {"type": "string"}},
            "required": ["claim_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_provider",
        "description": "Retrieve synthetic provider configuration for a provider_id from a claim.",
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {"provider_id": {"type": "string"}},
            "required": ["provider_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_edit_policy",
        "description": "Read the mock workflow guidance file for a rule_key on a fired edit. This is not a real policy determination.",
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "rule_key": {
                    "type": "string",
                    "enum": list(RULE_FILES),
                },
            },
            "required": ["rule_key"],
            "additionalProperties": False,
        },
    },
    {
        "name": "request_documentation",
        "description": "Queue a mock documentation request only for a fired edit marked information_needed. Does not contact a provider.",
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "claim_id": {"type": "string"},
                "edit_id": {"type": "string"},
                "document_type": {
                    "type": "string",
                    "enum": ["clinical_note", "authorization_record", "service_report", "other"],
                },
            },
            "required": ["claim_id", "edit_id", "document_type"],
            "additionalProperties": False,
        },
    },
    {
        "name": "create_review_task",
        "description": "Queue a mock human review for a fired edit. Never approves, denies, or changes a claim.",
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "claim_id": {"type": "string"},
                "edit_id": {"type": "string"},
                "reason": {"type": "string"},
            },
            "required": ["claim_id", "edit_id", "reason"],
            "additionalProperties": False,
        },
    },
]

SYSTEM_PROMPT = """You are an administrative assistant for a synthetic claims-editing exercise.
All records and policy files are fictional. Retrieve a claim before discussing it.
For provider-level edit frequency questions, use summarize_provider_edits, then read
each returned rule_key with get_edit_policy before explaining the rules.
Use the provider lookup when a fired edit concerns provider configuration. Read the
matching edit policy file before recommending a workflow. You may queue mock
requests for missing documentation or human review, but must never decide medical
necessity or coverage, or approve, deny, or alter a claim. Clearly identify mock
actions as mock actions in your final answer."""


def _ok(payload):
    return json.dumps(payload), False


def _error(category, message):
    return json.dumps({"error_category": category, "message": message}), True


def _find_edit(claim_id, edit_id):
    claim = CLAIMS_BY_ID.get(claim_id)
    if claim is None:
        return None, None
    for edit in claim["edits_fired"]:
        if edit["edit_id"] == edit_id:
            return claim, edit
    return claim, None


def get_claim(claim_id):
    claim = CLAIMS_BY_ID.get(claim_id)
    if claim is None:
        return _error("not_found", f"No synthetic claim found for {claim_id}.")
    return _ok(claim)


def get_provider(provider_id):
    provider = PROVIDERS_BY_ID.get(provider_id)
    if provider is None:
        return _error("not_found", f"No synthetic provider found for {provider_id}.")
    return _ok(provider)


def summarize_provider_edits(provider_id):
    if provider_id not in PROVIDERS_BY_ID:
        return _error("not_found", f"No synthetic provider found for {provider_id}.")

    provider_claims = [claim for claim in CLAIMS if claim["provider_id"] == provider_id]
    rule_counts = Counter(
        edit["rule_key"]
        for claim in provider_claims
        for edit in claim["edits_fired"]
    )
    category_counts = Counter(
        edit["category"]
        for claim in provider_claims
        for edit in claim["edits_fired"]
    )
    highest_count = max(rule_counts.values(), default=0)
    most_frequent = sorted(
        rule_key for rule_key, count in rule_counts.items()
        if count == highest_count
    )

    return _ok({
        "provider_id": provider_id,
        "claim_count": len(provider_claims),
        "claim_ids": [claim["claim_id"] for claim in provider_claims],
        "total_fired_edits": sum(rule_counts.values()),
        "rule_counts": dict(sorted(rule_counts.items())),
        "category_counts": dict(sorted(category_counts.items())),
        "most_frequent_rule_keys": most_frequent,
        "rule_keys_to_read": sorted(rule_counts),
    })


def get_edit_policy(rule_key):
    filename = RULE_FILES.get(rule_key)
    if filename is None:
        return _error("validation", f"Unknown edit rule key: {rule_key}.")
    policy_path = ASSET_DIR / "edit_rules" / filename
    return _ok({"rule_key": rule_key, "policy_text": policy_path.read_text(encoding="utf-8")})


def request_documentation(claim_id, edit_id, document_type):
    claim, edit = _find_edit(claim_id, edit_id)
    if claim is None:
        return _error("not_found", f"No synthetic claim found for {claim_id}.")
    if edit is None:
        return _error("validation", f"Edit {edit_id} is not attached to claim {claim_id}.")
    if edit["disposition"] != "information_needed":
        return _error("policy", "This edit is not marked as needing documentation.")

    request = {
        "request_id": f"DOC-{uuid.uuid4().hex[:8]}",
        "claim_id": claim_id,
        "edit_id": edit_id,
        "document_type": document_type,
        "status": "mock_request_queued",
    }
    DOCUMENTATION_REQUESTS.append(request)
    return _ok(request)


def create_review_task(claim_id, edit_id, reason):
    claim, edit = _find_edit(claim_id, edit_id)
    if claim is None:
        return _error("not_found", f"No synthetic claim found for {claim_id}.")
    if edit is None:
        return _error("validation", f"Edit {edit_id} is not attached to claim {claim_id}.")

    task = {
        "task_id": f"REV-{uuid.uuid4().hex[:8]}",
        "claim_id": claim_id,
        "edit_id": edit_id,
        "reason": reason,
        "status": "mock_review_queued",
        "queue": "claims_policy_review",
    }
    REVIEW_TASKS.append(task)
    return _ok(task)


HANDLERS = {
    "summarize_provider_edits": summarize_provider_edits,
    "get_claim": get_claim,
    "get_provider": get_provider,
    "get_edit_policy": get_edit_policy,
    "request_documentation": request_documentation,
    "create_review_task": create_review_task,
}


def execute_tool(name, tool_input):
    handler = HANDLERS.get(name)
    if handler is None:
        return _error("validation", f"Unknown tool {name}.")
    try:
        return handler(**tool_input)
    except Exception as exc:
        return _error("transient", f"{type(exc).__name__}: {exc}")


def run_agent(user_message, client=None, verbose=True):
    client = client or anthropic.Anthropic()
    messages = [{"role": "user", "content": user_message}]

    for turn in range(MAX_TURNS):
        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            tool_choice={"type": "any"} if turn == 0 else {"type": "auto"},
            messages=messages,
        )
        if verbose:
            print(f"turn {turn + 1}: stop_reason={response.stop_reason}")

        if response.stop_reason == "refusal":
            raise RuntimeError("The model refused this request.")
        if response.stop_reason == "max_tokens":
            raise RuntimeError("The response was cut off at max_tokens.")

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            return "".join(
                block.text for block in response.content if block.type == "text"
            )
        if response.stop_reason != "tool_use":
            raise RuntimeError(f"Unhandled stop_reason: {response.stop_reason}")

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            if verbose:
                print(f"calling tool: {block.name}")
            content, is_error = execute_tool(block.name, block.input)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": content,
                "is_error": is_error,
            })
        messages.append({"role": "user", "content": tool_results})

    raise RuntimeError(f"No final response after {MAX_TURNS} turns.")


if __name__ == "__main__":
    example = "Review claim CLM-1011 and explain what should happen with each fired edit."
    prompt = input("Claims request (Enter for example): ").strip() or example
    print(run_agent(prompt))
