"""Day 1 practice: strict tool schemas + code-side validation.

These tests start RED. Make them pass by editing support_agent/tools.py:
  1. Add a `list_orders` tool (definition in TOOLS + handler in HANDLERS).
  2. Validate ID formats (C###, O####) in code and return a `validation` error.
Run: .venv/bin/python -m pytest tests/test_day01.py -q
"""

import json

from support_agent import data, tools

UNSUPPORTED_IN_STRICT = {"minLength", "maxLength", "minimum", "maximum", "multipleOf"}


def _walk(schema):
    """Yield every dict nested inside a JSON schema."""
    if isinstance(schema, dict):
        yield schema
        for v in schema.values():
            yield from _walk(v)
    elif isinstance(schema, list):
        for v in schema:
            yield from _walk(v)


# --- schema lint: a guardrail that runs before any model call ---------------

def test_every_tool_is_strict_ready():
    for tool in tools.TOOLS:
        schema = tool["input_schema"]
        assert tool.get("strict") is True, tool["name"]
        assert schema["additionalProperties"] is False, tool["name"]
        assert set(schema["required"]) <= set(schema["properties"]), tool["name"]
        for node in _walk(schema):
            bad = UNSUPPORTED_IN_STRICT & node.keys()
            assert not bad, f"{tool['name']} uses {bad}; enforce that in code instead"


def test_every_tool_has_a_handler():
    assert {t["name"] for t in tools.TOOLS} == set(tools.HANDLERS)


# --- list_orders -------------------------------------------------------------

def test_list_orders_schema_uses_enum_for_status():
    tool = next(t for t in tools.TOOLS if t["name"] == "list_orders")
    status = tool["input_schema"]["properties"]["status"]
    assert set(status["enum"]) >= {"processing", "shipped", "delivered", "cancelled"}


def test_list_orders_returns_only_that_customers_orders():
    content, is_error = tools.execute_tool("list_orders", {"customer_id": "C001"})
    assert not is_error
    ids = {o["order_id"] for o in json.loads(content)["orders"]}
    assert ids == {"O1001", "O1002"}


def test_list_orders_filters_by_status():
    content, _ = tools.execute_tool("list_orders", {"customer_id": "C002", "status": "shipped"})
    assert [o["order_id"] for o in json.loads(content)["orders"]] == ["O1003"]
    content, _ = tools.execute_tool("list_orders", {"customer_id": "C002", "status": "delivered"})
    assert json.loads(content)["orders"] == []


# --- code-side format validation --------------------------------------------

def test_malformed_customer_id_is_validation_error():
    # Classic model mistake: passing the email where the id belongs.
    content, is_error = tools.execute_tool("list_orders", {"customer_id": "ana@example.com"})
    err = json.loads(content)
    assert is_error and err["error_category"] == "validation"
    assert "lookup_customer" in err["message"]  # tell the model how to recover


def test_malformed_order_id_is_validation_error_not_not_found():
    content, is_error = tools.execute_tool("get_order", {"order_id": "1001", "customer_id": "C001"})
    err = json.loads(content)
    assert is_error and err["error_category"] == "validation"
    assert "O####" in err["message"]

# --- Input validation format for refund -------------------------------------
def test_refund_rejects_malformed_order_id():
    content, is_error = tools.execute_tool(
        "issue_refund", {"order_id": "1001", "customer_id": "C001", "reason": "invalid"})
    assert is_error and json.loads(content)["error_category"] == "validation"
    assert data.REFUNDS == []

def test_refund_rejects_email_as_customer_id():
    content, is_error = tools.execute_tool(
        "issue_refund", {"order_id": "O1001", "customer_id": "ana@example.com", "reason": "invalid"})
    err = json.loads(content)
    assert is_error and err["error_category"] == "validation"
    assert "lookup_customer" in err["message"]  # tell the model how to recover
    assert data.REFUNDS == []



    
    