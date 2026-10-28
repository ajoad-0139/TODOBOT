# Task CRUD API Implementation Using FastAPI

Hello! I would like your help implementing the **Task CRUD API endpoints using FastAPI** for a task management application. Please follow the requirements and guidelines below carefully.

## 1. Project Objective

The application is a task manager where users will primarily interact with their tasks through an AI-powered chat interface. However, for this phase, I want to focus **exclusively on the backend CRUD operations for tasks**.

Please do not implement the AI agent, chat interface, semantic search, ChromaDB, or Qdrant at this stage. I want to establish a clean and reliable task management API first.

## 2. Task Data Model

Each task should contain the following fields:

- `id`: Unique identifier for each task.
- `title`: Required task title.
- `description`: Optional task description.
- `status`: Task status, such as `pending`, `in_progress`, or `completed`.
- `priority`: Task priority, such as `low`, `medium`, or `high`.
- `due_date`: Optional task deadline.
- `created_at`: Timestamp indicating when the task was created.
- `updated_at`: Timestamp indicating when the task was last updated.

Please use appropriate data types, sensible defaults, and proper validation. Keep the design simple and practical.

## 3. Required API Endpoints

Please implement the following endpoints:

### Create a task
- `POST /api/v1/tasks/`
- Accept task details in the request body.
- Validate the input and create a new task.
- Return the created task with its generated ID and timestamps.

### List tasks
- `GET /api/v1/tasks/`
- Return the list of existing tasks.
- Support optional filtering by status and priority if straightforward to implement.
- Use appropriate response schemas.

### Retrieve a single task
- `GET /api/v1/tasks/{task_id}`
- Return the requested task.
- Return a proper `404 Not Found` response if it does not exist.

### Update a task
- `PATCH /api/v1/tasks/{task_id}`
- Allow partial updates to fields such as title, description, status, priority, and due date.
- Update the `updated_at` timestamp appropriately.
- Validate the updated values and return the updated task.

### Change task status or complete a task
- Provide a straightforward way to update a task's status, preferably by reusing the update endpoint rather than introducing unnecessary endpoints.
- Ensure that completing a task sets its status to `completed`.

### Delete a task
- `DELETE /api/v1/tasks/{task_id}`
- Delete the specified task.
- Return a suitable success response, such as `204 No Content`.
- Return `404 Not Found` if the task does not exist.

## 4. Technical Requirements

- Use **FastAPI** for the API layer.
- Use **Pydantic** for request validation and response schemas.
- Use **SQLAlchemy** for database interactions.
- Use SQLite for initial development unless the existing project already uses another database.
- Ensure that tasks persist after application restarts.
- Use proper HTTP status codes and clear error responses.
- Keep database operations separate from request and response validation.
- Use dependency injection for database sessions.
- Ensure that partial updates do not accidentally overwrite fields the client has omitted.
- Follow basic SOLID and DRY principles without introducing unnecessary abstractions.

## 5. Suggested Project Structure

Please adapt this structure to the existing project if one is already available. Avoid creating unnecessary files.

```text
app/
├── main.py
├── core/
│   └── config.py
├── db/
│   ├── base.py
│   └── session.py
├── models/
│   └── task.py
├── schemas/
│   └── task.py
├── services/
│   └── task_service.py
└── api/
    └── v1/
        └── endpoints/
            └── tasks.py
```

Keep the responsibilities clear:
- **Models:** Define the database representation of a task.
- **Schemas:** Define and validate API request and response data.
- **Services:** Handle task-related business logic and database operations.
- **Endpoints:** Handle HTTP requests, call the service layer, and return responses.
- **Database session:** Manage database connectivity and session dependencies.

If a simpler structure is more appropriate for the existing project, please use it instead.

## 6. Validation and Error Handling

Please ensure that:

- Task titles cannot be empty or contain only whitespace.
- Optional fields can be omitted or explicitly set to `null` where appropriate.
- Status and priority accept only supported values.
- Invalid task IDs and nonexistent tasks produce appropriate errors.
- Invalid request bodies return clear validation errors.
- Missing fields in a PATCH request remain unchanged.
- Database sessions are properly managed and closed.
- Responses use consistent schemas and HTTP status codes.

Authentication, authorization, and multi-user task ownership are outside the scope of this phase unless the existing project already requires them.

## 7. Implementation Approach

Please implement this step by step:

1. Inspect the existing project structure and dependencies, if the project files are available.
2. Identify the necessary models, schemas, database configuration, services, and endpoints.
3. Explain the purpose of each component briefly before or alongside its implementation.
4. Provide complete, runnable code for each required file, including the correct imports.
5. Show how to install any missing dependencies and start the FastAPI application.
6. Demonstrate how to test every endpoint using Swagger UI at `/docs` or example HTTP requests.
7. Include basic tests for successful operations, validation failures, and nonexistent task IDs.

Please avoid overengineering, unnecessary design patterns, and unrelated features. Prioritize readable code, correct database handling, and a clear request-to-database flow.

## 8. Scope Boundaries

For this phase, implement only the task management CRUD functionality.

Do not implement:
- AI agents or LLM integration.
- Chat interfaces or conversation management.
- Semantic search or vector embeddings.
- ChromaDB or Qdrant integration.
- Task recommendations or automatic task planning.
- Frontend development.

The API should, however, be designed so that an AI agent can call these endpoints or their underlying service functions in a later phase.

**Expected outcome:** A working, persistent FastAPI task CRUD API with clean request and response schemas, appropriate validation, sensible error handling, and a simple, maintainable project structure.

Thank you! Please keep the implementation practical, easy to understand, and focused on the requirements above.