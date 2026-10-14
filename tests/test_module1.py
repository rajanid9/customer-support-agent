"""Module 1 tests. They run offline: FakeClient returns scripted responses
in place of Claude, so we test OUR loop and tools, not the model."""

import json
from types import SimpleNamespace as NS

import pytest

from support_agent import agent, data, tools


@pytest.fixture(autouse=True)
def reset_state():
    data.REFUNDS.clear()
    data.ESCALATIONS.clear()


def tool_use(id_, name, input_):
    return NS(type="tool_use", id=id_, name=name, input=input_)


def text(s):
    return NS(type="text", text=s)


class FakeClient:
    def __init__(self, responses):
        self._responses = iter(responses)
        self.calls = []
        self.beta = NS(messages=NS(create=self._create))

    def _create(self, **kwargs):
        # Copy messages: the agent mutates its list after this call returns.
        self.calls.append({**kwargs, "messages": list(kwargs["messages"])})
        return next(self._responses)


def final(status, actions, customer_id="C001"):
    return NS(stop_reason="end_turn", content=[text(json.dumps({
        "status": status, "customer_id": customer_id,
        "actions_taken": actions, "customer_message": "Done."}))])


# --- tools -----------------------------------------------------------------

def test_refund_within_policy():
    content, is_error = tools.execute_tool("issue_refund", {"order_id": "O1001", "customer_id": "C001", "reason": "defective"})
    assert not is_error and json.loads(content)["amount"] == 129.99


def test_refund_over_limit_is_blocked_in_code():
    content, is_error = tools.execute_tool("issue_refund", {"order_id": "O1002", "customer_id": "C001", "reason": "x"})
    assert is_error
    assert json.loads(content) == {"error_category": "policy", "retryable": False,
                                   "message": json.loads(content)["message"]}
    assert data.REFUNDS == []


def test_order_of_another_customer_is_permission_error():
    content, is_error = tools.execute_tool("get_order", {"order_id": "O1003", "customer_id": "C001"})
    assert is_error and json.loads(content)["error_category"] == "permission"


def test_handler_crash_becomes_retryable_error():
    content, is_error = tools.execute_tool("get_order", {"order_id": "O1001"})  # missing arg -> TypeError
    assert is_error and json.loads(content)["retryable"] is True


# --- loop ------------------------------------------------------------------

def test_loop_runs_tools_then_returns_structured_resolution():
    client = FakeClient([
        NS(stop_reason="tool_use", content=[tool_use("t1", "lookup_customer", {"email": "ana@example.com"})]),
        NS(stop_reason="tool_use", content=[tool_use("t2", "get_order", {"order_id": "O1001", "customer_id": "C001"})]),
        NS(stop_reason="tool_use", content=[tool_use("t3", "issue_refund", {"order_id": "O1001", "customer_id": "C001", "reason": "defective"})]),
        final("resolved", ["refunded O1001"]),
    ])
    result = agent.run_agent("refund please", client=client, verbose=False)

    assert result.status == "resolved"
    assert len(data.REFUNDS) == 1
    # The tool_result sent back must reference the tool_use id it answers.
    last_user_msg = client.calls[-1]["messages"][-1]
    assert last_user_msg["content"][0]["tool_use_id"] == "t3"


def test_parallel_tool_calls_return_in_one_message():
    client = FakeClient([
        NS(stop_reason="tool_use", content=[
            tool_use("a", "get_order", {"order_id": "O1001", "customer_id": "C001"}),
            tool_use("b", "get_order", {"order_id": "O1002", "customer_id": "C001"}),
        ]),
        final("resolved", []),
    ])
    agent.run_agent("status of both orders", client=client, verbose=False)
    results = client.calls[1]["messages"][-1]["content"]
    assert [r["tool_use_id"] for r in results] == ["a", "b"]


def test_policy_error_leads_to_escalation():
    client = FakeClient([
        NS(stop_reason="tool_use", content=[tool_use("t1", "issue_refund", {"order_id": "O1002", "customer_id": "C001", "reason": "x"})]),
        NS(stop_reason="tool_use", content=[tool_use("t2", "escalate_to_human", {
            "customer_id": "C001", "reason": "policy_exception", "summary": "Wants $749 refund; over limit."})]),
        final("escalated", ["escalated"]),
    ])
    result = agent.run_agent("refund my monitor", client=client, verbose=False)
    assert client.calls[1]["messages"][-1]["content"][0]["is_error"] is True
    assert result.status == "escalated" and len(data.ESCALATIONS) == 1


def test_max_tokens_is_an_error_not_a_success():
    client = FakeClient([NS(stop_reason="max_tokens", content=[text('{"status": "reso')])])
    with pytest.raises(agent.AgentError, match="max_tokens"):
        agent.run_agent("hi", client=client, verbose=False)


def test_runaway_loop_hits_safety_cap():
    looping = NS(stop_reason="tool_use", content=[tool_use("t", "lookup_customer", {"email": "x@y.z"})])
    client = FakeClient([looping] * agent.MAX_TURNS)
    with pytest.raises(agent.AgentError, match="No resolution"):
        agent.run_agent("hi", client=client, verbose=False)
