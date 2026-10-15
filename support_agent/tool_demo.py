import anthropic
import json

MODEL = "claude-opus-5"

TOOLS = [
    {
        "name": "calculator",
        "description": "Calculate a basic arithmetic operation.",
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "a": {"type": "number"},
                "b": {"type": "number"},
                "operation": {
                    "type": "string",
                    "enum": ["add", "subtract", "multiply", "divide"],
                },
            },
            "required": ["a", "b", "operation"],
            "additionalProperties": False,
        },
    },
    {
        "name": "web_search",
        "description": "Search the web. This demo is a stub and does not access the internet.",
        "strict": True,
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
]
def calculator(a, b, operation):
    if operation == "add":
        result = a + b
    elif operation == "subtract":
        result = a - b
    elif operation == "multiply":
        result = a * b
    elif operation == "divide":
        if b == 0:
            return {"error": "Cannot divide by zero."}
        result = a / b
    else:
        return {"error": "Unsupported operation."}

    return {"result": result}


def web_search(query):
    return {
        "status": "not_configured",
        "query": query,
        "results": [],
    }


HANDLERS = {
    "calculator": calculator,
    "web_search": web_search,
}

def run_agent(user_message):
    client = anthropic.Anthropic()
    messages = [{"role": "user", "content": user_message}]
    for turn in range(10):
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=(
                    "For arithmetic questions, always use the calculator tool; do not calculate mentally. "
                    "When the user asks for a numerical result using 'A by B' (for example, "
                     "'what is 10000 by 30000'), interpret 'by' as multiplication unless the context "
                     "clearly indicates dimensions or another meaning. Do not provide multiple "
                     "interpretations. If the meaning is still unclear, ask one concise clarification "
                     "question. The web_search tool is a stub; if it says search is not configured, "
                    "tell the user."
                   ),
              
            tools=TOOLS,
            tool_choice={"type": "any"} if turn == 0 else {"type": "auto"},
            messages=messages,
        )
        print(f"turn {turn + 1}: stop_reason={response.stop_reason}")
        messages.append({
            "role": "assistant",
            "content": response.content,
        })

        if response.stop_reason == "end_turn":
            return "".join(
                block.text for block in response.content
                if block.type == "text"
            )

        if response.stop_reason != "tool_use":
            raise RuntimeError(
                f"Unexpected stop reason: {response.stop_reason}"
            )

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            print(f"calling tool: {block.name}")
            handler = HANDLERS.get(block.name)
            try:
                if handler is None:
                    raise ValueError(f"Unknown tool: {block.name}")
                result = handler(**block.input)
                is_error = False
            except Exception as exc:
                result = {"error": str(exc)}
                is_error = True

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(result),
                "is_error": is_error,
            })

        messages.append({
            "role": "user",
            "content": tool_results,
        })

    raise RuntimeError("Claude did not finish within 10 turns.")


if __name__ == "__main__":
    prompt = input("You: ")
    print(run_agent(prompt))