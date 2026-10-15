import json
from types import SimpleNamespace as NS

import pytest

from support_agent import healthcare_demo as demo


@pytest.fixture(autouse=True)
def reset_mock_queues():
    demo.REVIEW_TASKS.clear()
    demo.DOCUMENTATION_REQUESTS.clear()


def test_claims_and_providers_are_connected_and_have_fired_edits():
    assert len(demo.CLAIMS) == 30
    assert len({claim["claim_id"] for claim in demo.CLAIMS}) == 30
    assert all(claim["edits_fired"] for claim in demo.CLAIMS)
    assert {claim["provider_id"] for claim in demo.CLAIMS} <= set(demo.PROVIDERS_BY_ID)
    assert all(edit["rule_key"] in demo.RULE_FILES for claim in demo.CLAIMS for edit in claim["edits_fired"])


def test_get_edit_policy_reads_only_known_rule_files():
    content, is_error = demo.get_edit_policy("authorization")

    assert not is_error
    assert "Synthetic workflow guidance" in json.loads(content)["policy_text"]
    _, is_error = demo.get_edit_policy("../../claims.json")
    assert is_error


def test_provider_edit_summary_counts_rules_and_returns_policy_keys():
    content, is_error = demo.summarize_provider_edits("PRV-201")

    assert not is_error
    summary = json.loads(content)
    assert summary["claim_count"] == 5
    assert summary["rule_counts"]["utilization"] == 2
    assert summary["most_frequent_rule_keys"] == ["utilization"]
    assert summary["rule_keys_to_read"] == [
        "authorization", "coding_provider", "documentation", "utilization"
    ]
    assert all(not demo.get_edit_policy(key)[1] for key in summary["rule_keys_to_read"])


def test_documentation_request_checks_claim_edit_and_disposition():
    content, is_error = demo.request_documentation(
        "CLM-1002", "CLM-1002-E01", "clinical_note"
    )

    assert not is_error
    assert json.loads(content)["status"] == "mock_request_queued"
    assert len(demo.DOCUMENTATION_REQUESTS) == 1

    _, is_error = demo.request_documentation(
        "CLM-1001", "CLM-1002-E01", "clinical_note"
    )
    assert is_error

    _, is_error = demo.request_documentation(
        "CLM-1001", "CLM-1001-E01", "clinical_note"
    )
    assert is_error


def tool_use(tool_id, name, tool_input):
    return NS(type="tool_use", id=tool_id, name=name, input=tool_input)


def text(value):
    return NS(type="text", text=value)


class FakeClient:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []
        self.messages = NS(create=self.create)

    def create(self, **kwargs):
        self.calls.append({**kwargs, "messages": list(kwargs["messages"])})
        return next(self.responses)


def test_agentic_loop_returns_tool_results_to_model():
    client = FakeClient([
        NS(stop_reason="tool_use", content=[tool_use(
            "t1", "get_claim", {"claim_id": "CLM-1001"}
        )]),
        NS(stop_reason="tool_use", content=[tool_use(
            "t2", "get_edit_policy", {"rule_key": "authorization"}
        )]),
        NS(stop_reason="end_turn", content=[text("Route for human authorization review.")]),
    ])

    result = demo.run_agent(
        "Review claim CLM-1001.", client=client, verbose=False
    )

    assert result == "Route for human authorization review."
    assert len(client.calls) == 3
    assert client.calls[1]["messages"][-1]["content"][0]["tool_use_id"] == "t1"
    assert client.calls[2]["messages"][-1]["content"][0]["tool_use_id"] == "t2"


def test_end_turn_returns_final_text_without_another_api_call():
    client = FakeClient([
        NS(stop_reason="end_turn", content=[text("Claim review complete.")]),
        NS(stop_reason="tool_use", content=[tool_use(
            "unused", "get_claim", {"claim_id": "CLM-1001"}
        )]),
    ])

    result = demo.run_agent("Thanks, that is all.", client=client, verbose=False)

    assert result == "Claim review complete."
    assert len(client.calls) == 1
