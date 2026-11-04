# Day 1: Strict Tool Schemas + Validation in Code

**Date:** 2026-11-03 · **Result:** 27/27 tests passing · **Quiz:** 5/5
**Code:** [support_agent/tools.py](../support_agent/tools.py) · **Tests:** [tests/test_day01.py](../tests/test_day01.py)

---

## What I built

| Piece | What it does |
|---|---|
| `list_orders` tool | Lists a customer's orders, with an optional `status` filter (enum) |
| `_check_id` helper | Checks ID formats (`C###`, `O####`) with a regex and returns a `validation` error if one is wrong |
| Guardrails in 3 handlers | `get_order`, `list_orders` and `issue_refund` reject malformed IDs before doing anything else |
| Day 1 tests | Schema lint, `list_orders` behavior, negative tests for bad IDs (including refunds) |

---

## Core concepts

### 1. Strict mode checks the shape. Code checks the meaning.
`strict: True` guarantees that Claude's tool input matches the schema, but only for the keywords strict mode supports.

| Strict schema **enforces** | Strict schema **does NOT enforce** (check these in code) |
|---|---|
| Types (`string`, `integer`…) | `minLength` / `maxLength` |
| `required` fields | `minimum` / `maximum` / `multipleOf` |
| `enum`, `const` | Business rules ("C001 owns O1001", "refund ≤ $500") |
| `additionalProperties: false` | ID formats like `C###` (an email is still "a string") |
| Formats like `email`, `date`, `uuid` | |

> `{"customer_id": "ana@example.com"}` **passes** strict mode, because it's a valid string. Only code can catch that it's the wrong kind of ID.

### 2. Hints are probabilistic. Code is deterministic.
- A description like *"format C###"* or *"e.g. C001"* is a **hint**. Claude usually follows it, but not every time.
- **If a rule must always hold, enforce it in code.** This idea comes up again in every guardrail.

### 3. Defense in layers
```
Claude's tool call
      │
      ▼
① Strict schema   → wrong types, missing fields, values outside the enum
      ▼
② Handler code    → wrong formats, wrong owner, policy violations
      ▼
③ Real work       → look up orders, issue the refund (side effects)
```
Put the cheapest checks first. Bad input should be rejected **before** any side effect, such as money moving.

### 4. Errors are instructions for the model
A good tool error has three parts:
```json
{
  "error_category": "validation",
  "message": "'ana@example.com' is not a valid id; expected format like C001. If you only have an email, call lookup_customer first.",
  "retryable": false
}
```
- **Category** tells Claude *whose* mistake it was:
  - `validation`: the model sent a malformed value, so it fixes it itself
  - `not_found`: the ID is well-formed but doesn't exist, so Claude asks the customer to double-check
  - `policy`: not allowed, so Claude escalates
  - `transient`: a temporary failure, so a retry may work
- **Message** gives the recovery step (*"call lookup_customer first"*), so Claude doesn't have to guess.
- **Return the error, don't raise it.** A crash breaks the agent loop. A structured error lets Claude recover.

### 5. Tool descriptions drive tool selection
A good description says three things:

| Part | Example from `list_orders` |
|---|---|
| What it does | "List a customer's orders, optionally filtered by status" |
| When to use it | "when the customer doesn't know their order ID" |
| When **not** to use it / what to do first | "use get_order if you have an order_id", "call lookup_customer first" |

Overlapping tools (`get_order` vs `list_orders`) **need** this, or Claude picks the wrong one.

---

## Code patterns to reuse

**A tool has three parts:**
```python
TOOLS = [ {...definition...} ]          # 1. what Claude SEES
def list_orders(...): ...               # 2. what actually RUNS
HANDLERS = {"list_orders": list_orders} # 3. connects name → function
```

**Optional field:** leave it out of `required`, and give it a default in the handler:
```python
"required": ["customer_id"]                                  # status not listed
def list_orders(customer_id: str, status: str | None = None):
```

**Enum:**
```python
"status": {"type": "string", "enum": ["processing", "shipped", "delivered", "cancelled"]}
```
Enum values must match the backend data **exactly**, including case.

**A deterministic format check you can reuse:**
```python
def _check_id(value, pattern, example, hint=""):
    if re.fullmatch(pattern, value):   # fullmatch = the WHOLE string must match
        return None
    return _error("validation", f"'{value}' is not a valid id; expected format like {example}. {hint}".strip(), False)

# first line(s) of each handler:
if err := _check_id(customer_id, r"C\d{3}", "C001", "If you only have an email, call lookup_customer first."):
    return err
```
- `r"C\d{3}"` means the letter C followed by exactly 3 digits
- `:=` (the walrus operator) assigns and checks in one line

**Return a dict, not a bare list.** `{"orders": [...]}` can grow later (for example `"count"`) without breaking callers.

---

## Testing concepts

### Happy-path vs negative tests
| Happy path | Negative |
|---|---|
| Good input, and checks that it works | **Deliberately bad input**, and checks that it's safely rejected |
| `list_orders("C001")` → 2 orders | `list_orders("ana@example.com")` → validation error |

In production, Claude calls the tools, not me, and it will sometimes send bad values. A negative test **proves the guardrail works before a real customer depends on it** (like a car crash test).

### Arrange → Act → Assert
```python
content, is_error = tools.execute_tool("list_orders", {"customer_id": "ana@example.com"})  # arrange + act
err = json.loads(content)
assert is_error and err["error_category"] == "validation"                                # assert
```

### Test the state, not just the response
```python
assert data.REFUNDS == []   # proves no money moved
```
An error response alone doesn't prove nothing happened. Buggy code could refund *and then* return an error.

### Reading pytest failures
| You see | It means | Fix |
|---|---|---|
| ✅ PASSED | The guardrail rejected the bad input | Nothing, this is the goal |
| ❌ `AssertionError` | The test ran, but the code behaved wrongly | Fix the **code under test** |
| ❌ `AttributeError` / `TypeError` / `NameError` | The test crashed before checking anything | Fix a **typo in the test** |

**Red → green:** a new guardrail test should fail with an `AssertionError` *before* the guardrail exists, and pass after. If it passes from the start, it isn't really testing anything.

### Schema lint as a guardrail
`test_every_tool_is_strict_ready` fails if any tool uses a constraint strict mode ignores. It stops me from relying on a rule the API won't enforce.

---

## Misunderstandings I cleared up

- **"Handlers catch exceptions."** Here a *tool handler* is the function that does the tool's job (like a web route handler). The `try/except` in `execute_tool` is a separate safety net for real crashes.
- **"Tests only check against current data."** Tests check *behavior*, including how the code handles bad input.
- **"Negative tests should produce an AssertionError."** When the guardrail works, a negative test **passes**. An AssertionError means the guardrail is missing.

---

## Things to remember ⭐
1. **Strict schemas check the shape. Code checks the meaning.**
2. **If a rule must always hold, enforce it in code.** Prompts are probabilistic.
3. **Errors are instructions:** category + retryable flag + recovery hint.
4. **Return errors, don't raise them**, so the agent can recover.
5. **Descriptions say what, when, and when not.**
6. **Every guardrail gets a negative test**, and for side-effecting tools, check the state too.
7. **Cheap checks first**, and always before side effects.

---

## Quiz and answers
1. **`not_found` → `validation` for `"1001"`: how does Claude's next step change?** Validation means *the model* sent a malformed value, so it fixes the format itself (`O1001`) or recovers with `list_orders`. Not found means the ID is well-formed but missing, so Claude asks the customer.
2. **Why isn't "format C###" in the description enough?** It's a probabilistic hint. `_check_id` enforces it every time.
3. **`quantity` between 1 and 10: schema or code?** Code. Strict mode doesn't support `minimum`/`maximum` (and the schema lint would fail).
4. **Why mention `lookup_customer` in the error?** It gives Claude the next step in the workflow, so the error is actionable.
5. **Why assert `data.REFUNDS == []`?** It proves the guardrail stopped before the side effect, not just that an error came back.

---

## Commands
```bash
cd /Users/rajanidevineni/ClaudeCertification/projects/customer-support-agent
.venv/bin/python -m pytest tests/test_day01.py -q      # Day 1 tests
.venv/bin/python -m pytest -q                          # all tests
.venv/bin/python -m pytest -q -k refund                # tests with "refund" in the name
cat -n tests/test_day01.py                             # view a file with line numbers
```
VS Code: **Ctrl + `** opens the terminal · **Cmd + P** quick-opens a file (`file.py:70` jumps to a line) · **Cmd + S** saves

---

**Next, Day 2:** structured errors and retries. Mark transient failures `retryable: true`, and make the agent loop retry those but **not** policy errors.
