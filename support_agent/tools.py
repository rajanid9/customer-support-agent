"""Tool definitions (what Claude sees) and handlers (what actually runs).

Exam concepts shown here:
- Tool descriptions are the main signal Claude uses to pick a tool, so each
  one says what it does, when to use it, and when NOT to use it.
- `strict: True` + `additionalProperties: False` guarantees tool inputs match
  the schema, so handlers don't have to defend against malformed arguments.
- Handlers return structured errors (category + retryable flag) instead of
  a bare "failed", so the model can decide: retry, ask the customer, or escalate.
- Business rules that MUST hold (refund limit) are enforced in code, not only
  in the prompt. Prompts are probabilistic; code is deterministic.
"""

import json
import uuid

from . import data

REFUND_LIMIT_USD = 500.00
REFUND_WINDOW_DAYS = 30

TOOLS = [
    {
        "name": "lookup_customer",
        "description": (
            "Find a customer by email address. Use this first whenever the customer "
            "gives an email and you need their customer_id. Returns id, name, and tier. "
            "Do not use this to look up orders."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {"email": {"type": "string", "description": "Customer email, e.g. ana@example.com"}},
            "required": ["email"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_order",
        "description": (
            "Get one order's details: item, total, status, and days since delivery. "
            "Requires the order_id (format O####) and the customer_id that owns it; "
            "the call fails if the order belongs to a different customer."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "Order id, e.g. O1001"},
                "customer_id": {"type": "string", "description": "Owner's customer id, e.g. C001"},
            },
            "required": ["order_id", "customer_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "issue_refund",
        "description": (
            f"Refund a delivered order to the original payment method. Only for orders "
            f"delivered within {REFUND_WINDOW_DAYS} days and totalling at most "
            f"${REFUND_LIMIT_USD:.0f}. Call get_order first to verify eligibility. "
            f"For anything outside these limits, use escalate_to_human instead."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string"},
                "customer_id": {"type": "string"},
                "reason": {"type": "string", "description": "One-sentence reason for the refund"},
            },
            "required": ["order_id", "customer_id", "reason"],
            "additionalProperties": False,
        },
    },
    {
        "name": "escalate_to_human",
        "description": (
            "Hand the case to a human agent. Use when: the customer explicitly asks for a "
            "human; the request is outside policy (e.g. refund over the limit or window); "
            "or you cannot make progress after trying the available tools. The summary must "
            "let a human act without re-reading the conversation."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "Customer id, or 'unknown'"},
                "reason": {
                    "type": "string",
                    "enum": ["customer_requested", "policy_exception", "unable_to_resolve"],
                },
                "summary": {
                    "type": "string",
                    "description": "What the customer wants, what you verified, what you already tried",
                },
            },
            "required": ["customer_id", "reason", "summary"],
            "additionalProperties": False,
        },
    },
]


def _ok(payload: dict) -> tuple[str, bool]:
    return json.dumps(payload), False


def _error(category: str, message: str, retryable: bool) -> tuple[str, bool]:
    # category: validation | not_found | permission | policy | transient
    return json.dumps({"error_category": category, "message": message, "retryable": retryable}), True


def lookup_customer(email: str) -> tuple[str, bool]:
    for c in data.CUSTOMERS.values():
        if c["email"].lower() == email.strip().lower():
            return _ok(c)
    return _error("not_found", f"No customer with email {email}. Ask the customer to confirm it.", False)


def get_order(order_id: str, customer_id: str) -> tuple[str, bool]:
    order = data.ORDERS.get(order_id)
    if order is None:
        return _error("not_found", f"Order {order_id} does not exist.", False)
    if order["customer_id"] != customer_id:
        return _error("permission", f"Order {order_id} does not belong to {customer_id}.", False)
    return _ok(order)


def issue_refund(order_id: str, customer_id: str, reason: str) -> tuple[str, bool]:
    order = data.ORDERS.get(order_id)
    if order is None or order["customer_id"] != customer_id:
        return _error("not_found", f"Order {order_id} not found for {customer_id}.", False)
    # Deterministic policy gate: holds even if the model ignores the tool description.
    if order["status"] != "delivered":
        return _error("policy", f"Order is '{order['status']}', only delivered orders can be refunded.", False)
    if order["days_since_delivery"] > REFUND_WINDOW_DAYS:
        return _error("policy", f"Outside {REFUND_WINDOW_DAYS}-day window. Escalate for an exception.", False)
    if order["total"] > REFUND_LIMIT_USD:
        return _error("policy", f"${order['total']:.2f} exceeds the ${REFUND_LIMIT_USD:.0f} auto-refund limit. "
                                "Escalate to a human.", False)
    if any(r["order_id"] == order_id for r in data.REFUNDS):
        return _error("validation", f"Order {order_id} was already refunded.", False)
    refund = {"refund_id": f"R-{uuid.uuid4().hex[:8]}", "order_id": order_id, "amount": order["total"], "reason": reason}
    data.REFUNDS.append(refund)
    return _ok(refund)


def escalate_to_human(customer_id: str, reason: str, summary: str) -> tuple[str, bool]:
    ticket = {"ticket_id": f"T-{uuid.uuid4().hex[:8]}", "customer_id": customer_id,
              "reason": reason, "summary": summary, "queue": "tier2_support"}
    data.ESCALATIONS.append(ticket)
    return _ok(ticket)


HANDLERS = {
    "lookup_customer": lookup_customer,
    "get_order": get_order,
    "issue_refund": issue_refund,
    "escalate_to_human": escalate_to_human,
}


def execute_tool(name: str, tool_input: dict) -> tuple[str, bool]:
    """Run a tool and return (content, is_error). Never raises: every failure
    goes back to Claude as a tool_result so it can recover."""
    handler = HANDLERS.get(name)
    if handler is None:
        return _error("validation", f"Unknown tool {name}.", False)
    try:
        return handler(**tool_input)
    except Exception as exc:  # backend outage, bug, etc.
        return _error("transient", f"{type(exc).__name__}: {exc}", True)
