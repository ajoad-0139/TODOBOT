# Build an AI-Powered Task Management Agent Using FastAPI, LangGraph, and Qdrant

Hello! I would like you to implement the core AI agent for my task management application. Please inspect the existing FastAPI project and its task CRUD endpoints, schemas, models, and services before making changes.

The objective is to build a conversational task management agent that understands natural-language instructions, determines which backend tools are required, executes them safely, retrieves relevant tasks through semantic search, and communicates with the client in real time through WebSockets.

**This task is strictly backend-only. Please do not implement or modify the frontend.**

Prioritize correctness, clear data flow, reliable persistence, safe tool execution, and a simple, maintainable implementation. Avoid overengineering.

## 1. Technology Stack

Use the following technologies:

- **FastAPI:** API framework and WebSocket endpoint.
- **LangGraph:** Agent workflow orchestration, state management, and conversational memory.
- **LangChain:** Only use components needed to integrate the LLM or tools with LangGraph; do not use a separate LangChain agent architecture.
- **Qdrant:** Vector database for semantic task search.
- **Sentence Transformers:** Lightweight local text embeddings, using a small model such as `sentence-transformers/all-MiniLM-L6-v2`.
- **SQLAlchemy:** Persistent task storage through the existing database implementation.
- **Pydantic:** Structured input, output, and tool argument validation.
- **Environment variables:** Store model configuration, API credentials, database connection strings, Qdrant settings, and other environment-specific configuration.

Use the existing project's dependencies and conventions where possible. Do not replace working infrastructure without a clear reason.

## 2. Agent Responsibilities

The agent must understand the user's message and determine the appropriate action or combination of actions.

It should support:

- Creating tasks.
- Listing tasks.
- Finding tasks using natural-language semantic search.
- Updating task details.
- Changing task status.
- Completing tasks.
- Deleting tasks.
- Asking clarifying questions when the target task or intended operation is ambiguous.
- Asking for explicit confirmation before executing an edit or deletion.

The agent must not execute arbitrary database queries or generate unrestricted database operations from LLM output.

Instead, expose a set of well-defined backend tools with validated arguments. The LLM should select the appropriate tool, provide structured arguments, and explain the result to the user.

## 3. Task Persistence and Qdrant Indexing

The relational database must remain the authoritative source of truth for all task records.

Qdrant must store vector embeddings and task identifiers for semantic retrieval. It must not become the primary storage location for task data.

### Task creation workflow

When the user requests a new task, follow this workflow:

1. The agent identifies the create-task operation.
2. Validate the extracted title, description, status, priority, and optional due date.
3. Create and commit the task through the existing task service and database session.
4. Obtain the persisted task ID from the database response.
5. Build the embedding text from the task's title, description, status, and priority.
6. Generate the embedding using the configured Sentence Transformers model.
7. Upsert the vector into Qdrant, storing the task ID in the payload.
8. Return a structured success response containing the task details.

For example, the embedding input could be:

```text
Title: Finish the demo
Description: Complete the product demonstration
Status: pending
Priority: high
```

Use a stable Qdrant point identifier derived from the persisted task ID, such as a UUID representation where appropriate. Store the original database task ID in the payload so that retrieved points can be resolved back to actual task records.

**Important reliability requirement:** Do not lose a successfully created task simply because embedding generation or Qdrant indexing fails. The database transaction must be committed independently of vector indexing, and indexing failures must be reported or retried through a reliable mechanism.

Prefer a simple, reliable approach that fits the existing project. If necessary, implement a lightweight retry or synchronization mechanism. Do not introduce a distributed architecture unless the requirements genuinely demand it.

## 4. Semantic Task Search

Implement semantic search as a dedicated backend tool that the agent can invoke when the user's request requires finding tasks by meaning rather than exact text matching.

Examples:

- "Find tasks related to documentation."
- "Show unfinished work for the upcoming demo."
- "Which tasks are about improving API performance?"
- "Find the task where I need to prepare the weekly report."

### Search workflow

1. Receive the user's search intent.
2. Convert it into a suitable search query.
3. Generate the query embedding using the same embedding model used for task indexing.
4. Query Qdrant for the top relevant task IDs.
5. Apply supported metadata filters where appropriate, such as status and priority.
6. Retrieve the corresponding current task records from the relational database.
7. Discard deleted or otherwise nonexistent task records.
8. Return the requested number of tasks, subject to the available relevant results.

Allow the search tool to accept a validated result limit and sensible defaults.

Do not assume that every vector returned by Qdrant represents an existing or up-to-date task. Always resolve returned IDs against the relational database before presenting task details.

For requests such as "Show all unfinished tasks related to documentation," combine semantic relevance with structured filtering. Use the existing database or supported Qdrant payload filters where appropriate.

Do not claim that semantic search has found every matching task. It retrieves relevant candidates based on similarity and configured retrieval limits.

## 5. Embedding Model Configuration

Use a lightweight local Sentence Transformers model for embeddings. Prefer `sentence-transformers/all-MiniLM-L6-v2` unless the existing project has a compatible alternative.

Requirements:

- Load the embedding model once and reuse it instead of reloading it for every request.
- Keep the model name configurable through an environment variable.
- Use the same model and embedding configuration for indexing and searching.
- Ensure the Qdrant vector dimensions match the configured model.
- Avoid unnecessarily calling an external embedding API.
- Keep embedding generation separate from task CRUD business logic.

For example, configuration may include:

```env
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=tasks
QDRANT_API_KEY=
```

These values are illustrative. Follow the project's existing configuration conventions and validate required settings during application startup.

## 6. Structured Agent Tools

Create narrowly scoped tools for the operations that the agent needs.

Possible tools include:

- `create_task`
- `list_tasks`
- `semantic_search_tasks`
- `get_task`
- `update_task`
- `delete_task`

Reuse existing CRUD services instead of duplicating database logic inside the agent tools.

Each tool should have:

- A clear name and description.
- Explicit, typed arguments.
- Pydantic validation or an equivalent validated input schema.
- Well-defined return values.
- Predictable error handling.
- No direct exposure of unrestricted database operations.

The agent should use these tools based on the meaning of the user's message, not simply because a message contains a particular keyword.

For example, a request to "show unfinished documentation tasks" may require semantic search and status filtering, whereas "create a high-priority task to finish the demo tomorrow" requires task creation.

Avoid implementing the same business logic in multiple tools.

## 7. LangGraph Agent Workflow

Use LangGraph to orchestrate the agent.

Create a graph with clear stages for understanding the request, determining the action, executing permitted tools, handling clarification or confirmation, and preparing the response.

A suitable high-level workflow is:

```text
User Message
    |
    v
Load Conversation State
    |
    v
Understand User Intent
    |
    v
Determine Required Action
    |
    +----> Simple Conversation
    |
    +----> List / Semantic Search
    |
    +----> Create Task
    |
    +----> Edit / Delete
                 |
                 v
       Identify Target Task
                 |
                 v
       Is Target Unambiguous?
          |              |
         No             Yes
          |              |
          v              v
     Clarify User    Request Explicit
                       Confirmation
                           |
                           v
                    Wait for Confirmation
                           |
                           v
                    Validate Decision
                           |
                           v
                    Execute Tool
                           |
                           v
                  Update Conversation State
                           |
                           v
                    Return Result
```

Adapt this workflow to LangGraph's actual state, node, edge, and checkpoint APIs.

The graph should distinguish between:

- Understanding the user's request.
- Selecting a tool and preparing its arguments.
- Requesting clarification.
- Requesting confirmation.
- Executing a tool.
- Handling tool errors.
- Generating a final response.

Do not allow the LLM to bypass confirmation requirements by directly calling a destructive or modifying tool.

## 8. Confirmation and Ambiguity Handling

Safety is a core requirement.

### Editing and deleting

Before any edit or deletion, the agent must identify the intended task and obtain explicit user confirmation.

For example:

User: "Change the priority of my API task to low."

Agent: "I found the task 'Improve API response time'. Do you want me to change its priority from High to Low?"

The agent must wait for confirmation before making the change.

For deletion:

User: "Delete the demo task."

Agent: "I found the task 'Prepare the product demo'. Are you sure you want to delete it?"

The task must not be deleted until the user confirms.

### Ambiguous targets

If multiple tasks could match the user's instruction, the agent must ask a clarifying question before requesting confirmation or executing the operation.

For example:

User: "Delete the report task."

Agent: "I found two tasks that could match: 'Prepare the weekly report' and 'Finalize the monthly report'. Which one would you like to delete?"

After the user identifies the intended task, request confirmation before deletion.

### Confirmation implementation requirements

- Store pending operations in server-side conversation state.
- Associate each pending operation with the intended task ID and validated arguments.
- Use an explicit confirmation state rather than relying solely on the LLM's conversational interpretation.
- Require an affirmative response before execution.
- Treat rejection or cancellation as cancellation of the pending operation.
- Do not interpret unrelated messages as confirmation.
- Do not execute a stale pending operation after a different operation replaces it.
- Revalidate that the target task still exists and is in an appropriate state immediately before execution.

The confirmation process must be enforced by application logic and the graph, not left solely to the LLM's instructions.

## 9. Persistent Conversation Memory

Use LangGraph's checkpointing mechanism for conversation memory.

Do not rely solely on a Python dictionary or an in-memory conversation history, because those will not reliably survive application restarts or work across multiple application workers.

Requirements:

- Assign a stable conversation or thread ID to each conversation.
- Use the LangGraph `thread_id` to identify the conversation state.
- Persist conversation checkpoints using an appropriate database-backed checkpointer.
- Restore conversation state when a client reconnects using the same conversation ID.
- Preserve relevant context, pending clarification questions, and confirmation state.
- Keep separate conversations isolated from one another.
- Prevent one user's conversation state from being accessible to another user when authentication is present.
- Store only the history and state needed for continued conversations.

Keep the checkpoint storage configuration separate from the task database configuration where appropriate.

Do not confuse conversation memory with task storage. Tasks must remain persistent in the relational database, independently of the agent's conversation history.

## 10. WebSocket Communication

Implement a FastAPI WebSocket endpoint for real-time agent communication.

For example:

`/ws/chat/{conversation_id}`

The exact route may follow the existing project's routing conventions.

The frontend will be built later, so focus only on the backend WebSocket protocol.

### Communication requirements

The client should be able to send structured messages, such as:

```json
{
  "type": "chat_message",
  "message": "Create a high-priority task to finish the demo tomorrow"
}
```

The server should respond with structured events, such as:

```json
{
  "type": "assistant_message",
  "message": "Your task has been created successfully."
}
```

Use appropriate event types for:

- Assistant responses.
- Tool execution status, if useful.
- Clarification requests.
- Confirmation requests.
- Operation success.
- Operation errors.
- Connection errors.

For confirmation, the server may send an event such as:

```json
{
  "type": "confirmation_required",
  "operation": "delete_task",
  "message": "Are you sure you want to delete this task?"
}
```

The client must then send a structured confirmation or cancellation event. Validate every incoming WebSocket message and handle malformed messages gracefully.

The examples above illustrate the protocol; define and implement a consistent Pydantic-validated event schema.

### WebSocket implementation details

- Handle connection acceptance and disconnection correctly.
- Associate each connection with its conversation ID.
- Restore the corresponding LangGraph checkpoint state.
- Process messages without blocking the event loop with long-running synchronous work.
- Send clear error responses when an operation fails.
- Handle reconnects without losing persisted conversation state.
- Avoid duplicate tool execution when a connection drops and a message is retried.
- Keep the WebSocket layer separate from task business logic and graph implementation.

Use a request or operation identifier where appropriate to support safe retries and duplicate-message detection.

Do not build the frontend, a streaming UI, or a separate chat server.

## 11. Validation, Error Handling, and Security

Implement robust validation and predictable failure handling.

- Validate tool arguments before execution.
- Validate task fields using the existing Pydantic schemas.
- Reject invalid status values, priorities, dates, and task IDs.
- Handle nonexistent tasks with clear errors.
- Handle LLM provider errors without crashing the WebSocket connection.
- Handle Qdrant connection failures and embedding errors.
- Do not expose API keys, stack traces, or sensitive internal information to clients.
- Avoid executing arbitrary Python code, raw SQL, or unrestricted tool arguments produced by the LLM.
- Keep confirmation and cancellation logic deterministic.
- Ensure that failed task operations do not produce success messages.
- Avoid silently reporting successful vector indexing when it has failed.

For ordinary API endpoints, use appropriate HTTP status codes. For WebSocket messages, use a consistent structured error-event format.

## 12. Environment Configuration

Keep secrets, model configuration, and infrastructure settings in environment variables.

Use a `.env` file for local development and ensure it is excluded from version control.

Provide a `.env.example` containing placeholder values, such as:

```env
LLM_PROVIDER=
LLM_MODEL=
LLM_API_KEY=

EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

DATABASE_URL=

QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
QDRANT_COLLECTION=tasks

LANGGRAPH_CHECKPOINT_DATABASE_URL=

AGENT_TEMPERATURE=0
```

Adapt the variables to the selected provider and existing project. Do not invent provider-specific configuration if the provider has not been selected.

Keep the LLM provider and model configurable. The embedding model should remain separate from the conversational LLM.

Never commit real credentials or hardcode secrets in source files.

## 13. Suggested Project Structure

Adapt the structure to the existing project instead of blindly creating duplicate modules.

```text
app/
├── main.py
├── core/
│   └── config.py
├── api/
│   └── websocket.py
├── agents/
│   ├── task_agent.py
│   ├── state.py
│   └── prompts.py
├── tools/
│   └── task_tools.py
├── services/
│   ├── task_service.py
│   ├── embedding_service.py
│   └── vector_service.py
├── db/
│   ├── session.py
│   └── checkpointer.py
├── schemas/
│   └── chat.py
└── models/
    └── task.py
```

Keep the implementation simple. Reuse existing task models, CRUD services, configuration, and database sessions wherever possible.

Do not create extra abstraction layers merely to match this example.

## 14. Example User Instructions to Support

The agent must correctly handle the following examples.

**Create a task**

"Create a high-priority task to finish the demo tomorrow."

Expected behavior:
- Extract the title, priority, and due date.
- Ask for clarification if a required detail cannot be reasonably determined.
- Create the task through the existing task service.
- Commit the task to the relational database.
- Generate and index its embedding in Qdrant.
- Return a clear success response.

**Semantic search**

"Show all unfinished tasks related to documentation."

Expected behavior:
- Recognize the semantic search intent.
- Apply an unfinished-status filter.
- Retrieve relevant task IDs from Qdrant.
- Fetch the corresponding current records from the database.
- Return the available relevant tasks without claiming exhaustive results.

**Update task status**

"Move the demo task to In progress and mark the weekly report Done."

Expected behavior:
- Identify both requested task operations.
- Resolve each task unambiguously.
- Present the proposed changes and obtain confirmation before execution.
- Execute only after confirmation.
- Report the result of each operation separately.

**Change task priority**

"Change the priority of the API task to Low."

Expected behavior:
- Identify the intended task.
- Ask for clarification if multiple tasks match.
- Present the proposed change and obtain confirmation.
- Update the task in the database.
- Refresh or synchronize its Qdrant embedding so that subsequent searches reflect the new priority.
- Return the updated task details.

## 15. Implementation Workflow

Please implement the feature incrementally.

1. Inspect the existing FastAPI application, task CRUD implementation, database models, schemas, and dependencies.
2. Explain how the agent will reuse the existing backend tools and services.
3. Define the structured agent state, WebSocket event schemas, and tool contracts.
4. Implement and test the embedding service and Qdrant collection setup.
5. Implement semantic indexing and search.
6. Implement the LangGraph workflow and its tool integration.
7. Implement confirmation, clarification, and persistent conversation checkpointing.
8. Implement the WebSocket endpoint and structured event protocol.
9. Add configuration variables and update dependency files.
10. Add tests for task operations, semantic retrieval, confirmation flows, persistence, and WebSocket communication.
11. Verify the application starts and document how to run the required services.

Provide complete code for every new or modified file, including imports and configuration changes. Explain the important data flows briefly and identify any assumptions that depend on the existing project.

Do not rewrite unrelated functionality or make speculative changes to the existing CRUD implementation.

## 16. Acceptance Criteria

The implementation is complete when:

- The agent can create, list, search, update, complete, and delete tasks using validated backend tools.
- Task records persist across application restarts.
- Task embeddings and IDs are indexed in Qdrant.
- Semantic search retrieves relevant task IDs and resolves them against the authoritative database.
- Updates keep the vector index synchronized, with a reliable recovery strategy for indexing failures.
- Ambiguous targets trigger clarification.
- Edits and deletions require explicit confirmation before execution.
- Conversation state and pending confirmations survive reconnects and application restarts through persistent LangGraph checkpoints.
- The WebSocket endpoint exchanges validated, structured messages and events.
- Failures are handled without falsely reporting successful operations.
- Configuration and credentials are managed through environment variables.
- Automated tests cover the critical workflows.
- No frontend code is implemented.

**Final instruction:** Please focus on building a reliable, maintainable task agent, not a complex autonomous framework. Use LangGraph for explicit workflow control and persistent conversation state, Qdrant for semantic retrieval, and the existing relational database for task persistence. Keep each responsibility separate, make destructive and modifying actions safe, and ensure that the implementation is practical to understand and extend.