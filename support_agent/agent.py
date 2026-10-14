"""Module 1: a hand-written agentic loop.

The SDK's tool runner can drive this loop for you. We write it by hand once
so each step is visible, because the exam tests these mechanics:

  1. Send messages + tools to Claude.
  2. Branch on `stop_reason`, never on the wording of the reply:
       tool_use   -> run the tools, append the results, loop again
       end_turn   -> finished; parse the final answer
       max_tokens -> output was cut off (error, not success)
       refusal    -> Claude declined; handle it before reading content
  3. Append the full `response.content` (not only the text) so tool_use ids
     and thinking blocks stay in the history.
  4. Return every tool_result for one turn in a single user message.

MAX_TURNS is a safety net against runaway loops. It is not how the loop is
meant to end; `end_turn` is.
"""

import json
import sys
from typing import Literal

import anthropic
from pydantic import BaseModel

from .tools import TOOLS, execute_tool

MODEL = "claude-opus-5"
MAX_TURNS = 10

SYSTEM_PROMPT = """You are a customer support agent for an electronics store.

Verify the customer (lookup_customer) before looking at or changing any order.
Check an order with get_order before refunding it.
Escalate with escalate_to_human when the customer asks for a person, when the
request is outside policy, or when you cannot make progress. Do not escalate
just because the customer sounds upset if you can still solve the problem.
If a tool returns an error, read its error_category: fix the input and retry
only when it says retryable; otherwise ask the customer or escalate.

When you are done, reply with the resolution JSON."""


class Resolution(BaseModel):
    """The structured final answer, checked by pydantic after the loop."""
    status: Literal["resolved", "escalated", "needs_customer_info"]
    customer_id: str | None
    actions_taken: list[str]
    customer_message: str


# JSON schema for output_config.format. Written by hand so it only uses
# features structured outputs supports (additionalProperties false, required).
RESOLUTION_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["resolved", "escalated", "needs_customer_info"]},
        "customer_id": {"type": ["string", "null"]},
        "actions_taken": {"type": "array", "items": {"type": "string"}},
        "customer_message": {"type": "string", "description": "Reply to send to the customer"},
    },
    "required": ["status", "customer_id", "actions_taken", "customer_message"],
    "additionalProperties": False,
}


class AgentError(RuntimeError):
    pass


def run_agent(user_message: str, client=None, verbose: bool = True) -> Resolution:
    client = client or anthropic.Anthropic()
    messages = [{"role": "user", "content": user_message}]

    for turn in range(1, MAX_TURNS + 1):
        response = client.beta.messages.create(
            model=MODEL,
            max_tokens=16000,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
            output_config={"format": {"type": "json_schema", "schema": RESOLUTION_SCHEMA}},
            # If a safety classifier declines, retry server-side on Anthropic's
            # recommended fallback model instead of failing the request.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )

        if response.stop_reason == "refusal":
            raise AgentError("Claude declined this request; route it to a human.")
        if response.stop_reason == "max_tokens":
            raise AgentError("Response was cut off at max_tokens.")

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            final_text = [b.text for b in response.content if b.type == "text"][-1]
            return Resolution.model_validate_json(final_text)

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                content, is_error = execute_tool(block.name, block.input)
                if verbose:
                    flag = "ERROR " if is_error else ""
                    print(f"[turn {turn}] {block.name}({json.dumps(block.input)}) -> {flag}{content}")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": content,
                    "is_error": is_error,
                })
            messages.append({"role": "user", "content": tool_results})
            continue

        raise AgentError(f"Unhandled stop_reason: {response.stop_reason}")

    raise AgentError(f"No resolution after {MAX_TURNS} turns.")


if __name__ == "__main__":
    request = " ".join(sys.argv[1:]) or (
        "Hi, I'm ana@example.com. My headphones from order O1001 stopped working. Can I get a refund?"
    )
    print(run_agent(request).model_dump_json(indent=2))
