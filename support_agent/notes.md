### Customer Support Agent ####

Scenario 1 - Production data shows that in 12% of cases, your agent skips get_customer entirely and
calls lookup_order using only the customer's stated name, occasionally leading to misidentified
accounts and incorrect refunds. What change would most effectively address this reliability issue?

Ensure Deterministic Response - Specific tool sequence needed for critical business logic
Programmatic enforcements provide deterministic guarantees that prompt based approaches cannot 
- Add a programming pre-requisite that blocks lookup_order and process_refund until get_customer has returned a verified customer_id

Scenario 2 - Production logs show the agent frequently calls get_customer when users ask about
orders (e.g., "check my order #12345"), instead of calling lookup_order. Both tools have minimal
descriptions ("Retrieves customer information" / "Retrieves order details") and accept similar
identifier formats. What's the most effective first step to improve tool selection reliability?

Tool descriptions are primary mechanism LLM's use for tool selection. When desc are not clear, model lacks context to differentiate between similar tools

should be clear with boundaries, examples, edge cases explaining when to use vs other similar tools

Scenario 3 - Your agent achieves 55% first-contact resolution, well below the 80% target. Logs show it
escalates straightforward cases (standard damage replacements with photo evidence) while
attempting to autonomously handle complex situations requiring policy exceptions. What's the most
effective way to improve escalation calibration?

Unclear decision boundaries - Instructions/Prompt engineering - Explicitly mention escalation criteria with few shot examples demonstrating when to escalate vs resolve autonomously

### Code generation with Claude Code
Scenario 4 - You want to create a custom /review slash command that runs your team's standard code
review checklist. This command should be available to every developer when they clone or pull the
repository. Where should you create this command file?

Project scoped custom slash commands should be stored in the .claude/commands/ directory in the project repository
These commands are version controlled and available to all developers when they clone or pull the repo

Claude.MD is for project instructions and context not command definitions


Scenario 5: You've been assigned to restructure the team's monolithic application into microservices.
This will involve changes across dozens of files and requires decisions about service boundaries and
module dependencies. Which approach should you take?
Enter plan mode to explore the codebase, understand dependencies, and design an
implementation approach before making changes

Plan mode is designed for complex tasks - large scale changes, multiple valid approaches and architectural decisions


Scenario 6: Your codebase has distinct areas with different coding conventions: React components
use functional style with hooks, API handlers use async/await with specific error handling, and
database models follow a repository pattern. Test files are spread throughout the codebase alongside
the code they test (e.g., Button.test.tsx next to Button.tsx), and you want all tests to follow the same
conventions regardless of location. What's the most maintainable way to ensure Claude automatically
applies the correct conventions when generating code?

Rules 
Create rule files in .claude/rules/ with YAML frontmatter specifying glob patterns to conditionally
apply conventions based on file paths
Allows conventions to be automatically applied on file paths regardless of directory location because test files are spread throughout the codebase


### Multi-agent research system ###
Scenario 7: After running the system on the topic "impact of AI on creative industries," you observe
that each subagent completes successfully: the web search agent finds relevant articles, the
document analysis agent summarizes papers correctly, and the synthesis agent produces coherent
output. However, the final reports cover only visual arts, completely missing music, writing, and film
production. When you examine the coordinator's logs, you see it decomposed the topic into three
subtasks: "AI in digital art creation," "AI in graphic design," and "AI in photography." What is the most
likely root cause?

The coordinator agent's task decomposition is too narrow, resulting in subagent assignments that
don't cover all relevant domains of the topic
As logs reveal only 3 topics - it decomposed creative industries into only visual arts subtasks and didnt include music, writing and film


Scenario 8: The web search subagent times out while researching a complex topic. You need to design
how this failure information flows back to the coordinator agent. Which error propagation approach
best enables intelligent recovery?

Return structured error context to the coordinator including the failure type, the attempted query,
any partial results, and potential alternative approaches.
Structured error context gives coordinator info it needs to make intelligent recovery decisions - what to do next? Retry with a modified query, try an alternate approach or proceed with partial  results

Scenario 9: During testing, you observe that the synthesis agent frequently needs to verify specific
claims while combining findings. Currently, when verification is needed, the synthesis agent returns
control to the coordinator, which invokes the web search agent, then re-invokes synthesis with results.
This adds 2-3 round trips per task and increases latency by 40%. Your evaluation shows that 85% of
these verifications are simple fact-checks (dates, names, statistics) while 15% require deeper
investigation. What's the most effective approach to reduce overhead while maintaining system
reliability?

Give the synthesis agent a scoped verify_fact tool for simple lookups, while complex verifications
continue delegating to the web search agent through the coordinator.

Give the synthesis agent what it needs for simple fact verification while preserving coordination pattern for complex cases


### Claude Code for Continuous Integration ###
Scenario 10: Your pipeline script runs claude "Analyze this pull request for security issues" but the job
hangs indefinitely. Logs indicate Claude Code is waiting for interactive input. What's the correct
approach to run Claude Code in an automated pipeline?

Add the -p flag: claude -p "Analyze this pull request for security issues"

-p or print flag runs claude code in non-interactive mode. It processes the prompt, outputs the result to stdout and exits without waiting for user input which is what CI/CD pipelines require


Scenario 11: Your team wants to reduce API costs for automated analysis. Currently, real-time Claude
calls power two workflows: (1) a blocking pre-merge check that must complete before developers can
merge, and (2) a technical debt report generated overnight for review the next morning. Your manager
proposes switching both to the Message Batches API for its 50% cost savings. How should you
evaluate this proposal?

Use batch processing for the technical debt reports only; keep real-time calls for pre-merge
checks.

MessageBatchesAPI offers 50% cost savings but increases latency - processing time can be up to 24 hours with no guaranteed latency SLA. Not suitable for blocking pre0merge checks as developers wait for results
More suitable for reports 

Scenario 12: A pull request modifies 14 files across the stock tracking module. Your single-pass review
analyzing all files together produces inconsistent results: detailed feedback for some files but
superficial comments for others, obvious bugs missed, and contradictory feedback—flagging a pattern
as problematic in one file while approving identical code elsewhere in the same PR. How should you
restructure the review?

Split into focused passes: analyze each file individually for local issues, then run a separate
integration-focused pass examining cross-file data flow

File by File analysis ensure consistent depth while a separate integration pass catches cross-file issues.





