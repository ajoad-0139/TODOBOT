# TaskFlow – AI Task Manager

A task manager you control by chatting. Ask the assistant in plain English to create, find, update, complete or delete tasks. Edits and deletions always ask for your confirmation first.

- **Backend:** FastAPI, LangGraph agent, SQLAlchemy (SQLite), Qdrant (semantic search), Sentence Transformers
- **Frontend:** React, TypeScript, Tailwind CSS
- **Chat transport:** WebSocket

---

## Features

- Task CRUD REST API (`/api/v1/tasks/`) with validation and filtering
- Conversational agent that picks validated tools based on the meaning of your message
- Semantic search ("show unfinished tasks about documentation") backed by Qdrant
- Safe edits and deletes: the agent asks which task you mean when it is ambiguous, then asks for explicit confirmation
- Conversation memory that survives reloads and server restarts (LangGraph checkpoints)
- Task board that refreshes automatically after the assistant changes something

---

## How it works

```text
Browser (React)
   │  REST: GET /api/v1/tasks/            → task board
   │  WebSocket: /ws/chat/{conversation_id} → chat
   ▼
FastAPI
   ├─ api/routes/tasks.py     REST endpoints (thin)
   ├─ api/websocket.py        validates messages, calls the agent, sends events
   ├─ agents/task_agent.py    LangGraph workflow
   ├─ tools/task_tools.py     the only operations the agent may perform
   ├─ services/               task CRUD, embeddings, Qdrant, index sync
   └─ db/                     SQLAlchemy session + LangGraph checkpointer

SQLite (tasks)         ← source of truth for all task data
Qdrant (vectors)       ← embeddings + task IDs only, for semantic search
SQLite (checkpoints)   ← conversation memory, separate from tasks
```

### The safety model

1. The LLM only **proposes** tool calls. It never runs SQL or modifies data directly.
2. `update_task` and `delete_task` only **prepare** a step. The agent resolves the target task and, if several tasks match, asks you which one you mean.
3. A pending operation is stored in server-side state with its own `operation_id`.
4. Execution happens only after a `confirm` message with the matching `operation_id` (or a typed "yes"). Any other message cancels the pending operation.
5. Right before executing, the task is re-checked: it must still exist and be unchanged since the proposal.

### Search and indexing

- Qdrant only stores vectors plus `{task_id, status, priority}`.
- Search results are always re-read from the database, so deleted or changed tasks never show stale data.
- A task is saved to the database first. Indexing into Qdrant happens afterwards, and a background loop re-indexes anything that failed or went out of sync, so a Qdrant outage never loses a task.

---

## Prerequisites

- Python 3.12
- Node.js 18+ and npm
- Docker (for Qdrant)
- An LLM API key (this project is set up for Groq, but the provider is configurable)

---

## Project structure

```text
AI_AUTOMATION/
├── run.sh                      # starts Qdrant, backend and frontend
├── server/
│   ├── main.py                 # runs uvicorn (app.create_app:app)
│   ├── requirements.txt
│   ├── .env                    # your local config (not committed)
│   ├── .env.example
│   ├── app/
│       ├── create_app.py       # FastAPI app, lifespan, CORS, routers
│       ├── core/config.py
│       ├── errors/task_exceptions.py
│       ├── api/
│       │   ├── routes/tasks.py
│       │   └── websocket.py
│       ├── agents/             # task_agent.py, state.py, prompts.py
│       ├── tools/task_tools.py
│       ├── services/           # task, embedding, vector, index sync
│       ├── db/                 # base, session, checkpointer
│       ├── models/             # task, task_index_state
│       └── schemas/            # task, chat
│   
└── client/
    └── src/
        ├── Components/         # Tasks/, Chat/
        ├── Pages/Home.tsx
        ├── Services/           # taskService.ts, chatService.ts
        ├── Types/              # task.ts, chat.ts
        └── App.tsx
```

---

## Setup

### 1. Backend

```bash
cd server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install langchain-groq        # or the package for your LLM provider
cp .env.example .env
```

Edit `server/.env`:

```env
LLM_PROVIDER=groq
LLM_MODEL=<your Groq model name>
LLM_API_KEY=<your API key>
AGENT_TEMPERATURE=0
AGENT_HISTORY_MESSAGES=30

EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

DATABASE_URL=sqlite:///./tasks.db

QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
QDRANT_COLLECTION=tasks

LANGGRAPH_CHECKPOINT_DATABASE_URL=sqlite:///./checkpoints.db

# Optional tuning (defaults shown)
SEARCH_MIN_SCORE=0.25
TARGET_AMBIGUITY_MARGIN=0.08
INDEX_SYNC_INTERVAL_SECONDS=30
```

`LLM_PROVIDER` and `LLM_MODEL` are required; the server refuses to start without them. Never commit `.env`.

### 2. Frontend

```bash
cd client
npm install
```

Optional `client/.env`:

```env
VITE_API_BASE_URL=http://localhost:8000
# VITE_WS_BASE_URL=ws://localhost:8000   (derived from the API URL if omitted)
```

---

## Running

### One command

```bash
chmod +x run.sh
./run.sh          # starts Qdrant (Docker), backend and frontend in separate terminals
./run.sh stop     # stops the Qdrant container
```

### Manually

```bash
# Terminal 1 – Qdrant
docker run -d --name qdrant -p 6333:6333 -v "$(pwd)/qdrant_storage:/qdrant/storage" qdrant/qdrant

# Terminal 2 – backend
cd server && source venv/bin/activate && python3 main.py

# Terminal 3 – frontend
cd client && npm run dev
```

| Service  | URL                          |
|----------|------------------------------|
| Frontend | http://localhost:3000        |
| Backend  | http://127.0.0.1:8000        |
| API docs | http://127.0.0.1:8000/docs   |
| Qdrant   | http://localhost:6333        |

The first backend start downloads the embedding model, so it can take a minute.

---

## Using the assistant

Try messages like:

- "Create a high-priority task to finish the demo tomorrow"
- "Show all unfinished tasks related to documentation"
- "Move the demo task to In progress and mark the weekly report Done"
- "Change the priority of the API task to Low"
- "Delete the report task"

For anything that changes or deletes a task, the assistant shows what it is about to do with **Confirm** and **Cancel** buttons. If more than one task matches, it asks you to pick one first.

---

## REST API

Base path: `/api/v1/tasks`

| Method | Path          | Description                                              |
|--------|---------------|----------------------------------------------------------|
| POST   | `/`           | Create a task (201)                                      |
| GET    | `/`           | List tasks. Filters: `status`, `priority`, `skip`, `limit` |
| GET    | `/{task_id}`  | Get one task (404 if missing)                            |
| PATCH  | `/{task_id}`  | Partial update; also used to change status               |
| DELETE | `/{task_id}`  | Delete a task (204)                                      |

Task fields: `id`, `title`, `description`, `status` (`pending` / `in_progress` / `completed`), `priority` (`low` / `medium` / `high`), `due_date`, `created_at`, `updated_at`. All timestamps are UTC.

---

## WebSocket protocol

Endpoint: `ws://localhost:8000/ws/chat/{conversation_id}`
(`conversation_id`: 8–64 letters, digits, `-` or `_`)

### Client → server

```json
{"type": "chat_message", "request_id": "abc123", "message": "Delete the demo task"}
{"type": "confirm",      "request_id": "abc124", "operation_id": "…"}
{"type": "cancel",       "request_id": "abc125", "operation_id": "…"}
```

Sending the same `request_id` again returns the stored result instead of repeating the operation, so retries after a dropped connection are safe.

### Server → client events

| Event                   | Meaning                                                   |
|-------------------------|-----------------------------------------------------------|
| `connection_ready`      | Connected. A pending confirmation is re-sent right after. |
| `assistant_message`     | Normal reply                                              |
| `clarification_request` | Several tasks match; `data.candidates` lists them         |
| `confirmation_required` | Needs confirm or cancel; includes `operation_id`          |
| `operation_success`     | A confirmed step was applied                              |
| `operation_error`       | A confirmed step failed, or nothing was pending           |
| `operation_cancelled`   | A pending operation was cancelled or replaced             |
| `tool_status`           | A tool finished (`data.tool`, `data.ok`)                  |
| `error`                 | Invalid message or internal error (`data.code`)           |

---



## Troubleshooting

**`Tool call validation failed ... due_date ... not valid date-time` (Groq)**
The provider validates tool arguments against the JSON schema. Tool schemas here use a plain string for `due_date` (parsed and strictly validated on the server). If you see a similar error for another field, loosen that field's type in `app/tools/task_tools.py` the same way.

**Task board shows "Could not load tasks"**
Check that the backend is running and that `VITE_API_BASE_URL` points to it. The CORS middleware in `create_app.py` currently allows `GET` only, which is enough for the board; widen `allow_methods` if the frontend ever needs to send POST, PATCH or DELETE directly. WebSocket connections are not affected by CORS.

**Chat shows "Reconnecting..."**
The backend is not reachable or failed at startup. Check the backend terminal; common causes are missing `LLM_PROVIDER` / `LLM_MODEL` or Qdrant not running.

**Qdrant errors on startup**
Make sure the container is running (`docker ps`) and `QDRANT_URL` matches. If you change `EMBEDDING_MODEL`, use a new `QDRANT_COLLECTION` name because vector sizes must match.

**Semantic search returns nothing or too much**
Tune `SEARCH_MIN_SCORE` (higher = stricter) in `.env`. Use `TARGET_AMBIGUITY_MARGIN` to control how close two matches must be before the assistant asks which one you mean.

**Start a fresh chat**
Delete `taskflow_conversation_id` and `taskflow_chat_messages` from the browser's local storage.

---
