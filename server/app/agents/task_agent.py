import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage, trim_messages
from langgraph.graph import END, START, StateGraph
from pydantic import ValidationError

from app.agents.prompts import RESPONSE_SUFFIX, clarification_context, system_prompt
from app.agents.state import AgentState
from app.core.config import Settings
from app.tools import task_tools as tools

logger = logging.getLogger(__name__)

CONFIRM_WORDS = {"yes", "y", "yep", "yeah", "confirm", "confirmed", "go ahead", "do it", "proceed", "yes please"}
CANCEL_WORDS = {"no", "n", "nope", "cancel", "stop", "never mind", "nevermind", "abort"}


def build_llm(settings: Settings):
    from langchain.chat_models import init_chat_model

    kwargs: dict[str, Any] = {"temperature": settings.AGENT_TEMPERATURE}
    if settings.LLM_API_KEY:
        kwargs["api_key"] = settings.LLM_API_KEY
    return init_chat_model(settings.LLM_MODEL, model_provider=settings.LLM_PROVIDER, **kwargs)


def _event(type_: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"type": type_, "message": message, **extra}


def _text(message) -> str:
    content = message.content
    if isinstance(content, str):
        return content.strip()
    return "".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in content).strip()


def _clarification_text(c: dict) -> str:
    lines = "\n".join(f'{i}. "{x["title"]}" (#{x["id"]})' for i, x in enumerate(c["candidates"], 1))
    return f'I found {len(c["candidates"])} tasks that could match "{c["target"]}":\n{lines}\nWhich one do you mean?'


def _confirmation_text(steps: list[dict]) -> str:
    if len(steps) == 1:
        return f'{steps[0]["summary"]}. Do you want me to go ahead?'
    lines = "\n".join(f'{i}. {s["summary"]}' for i, s in enumerate(steps, 1))
    return f"I'm about to make these changes:\n{lines}\nDo you want me to go ahead with all of them?"


class TaskAgent:
    """LangGraph workflow: intake -> understand -> run tools -> (respond) -> announce,
    plus a separate confirm/cancel path. Modifying steps only run in confirm_execute."""

    def __init__(self, ctx: tools.ToolContext, llm, checkpointer, history_messages: int = 30):
        self.ctx = ctx
        self.llm = llm.bind_tools(tools.TOOL_SCHEMAS)
        self.history_messages = history_messages
        self._locks: dict[str, asyncio.Lock] = {}
        self.graph = self._build_graph(checkpointer)

    # ---------- public API ----------
    async def run_turn(
        self,
        thread_id: str,
        *,
        request_id: str,
        message: str | None = None,
        decision: str | None = None,
        operation_id: str | None = None,
    ) -> list[dict[str, Any]]:
        config = {"configurable": {"thread_id": thread_id}}
        turn_input = {
            "request_id": request_id,
            "user_message": message,
            "decision": decision,
            "decision_operation_id": operation_id,
        }
        lock = self._locks.setdefault(thread_id, asyncio.Lock())
        async with lock:  # one turn at a time per conversation (single process)
            result = await self.graph.ainvoke(turn_input, config)
        return result.get("events", [])

    async def get_pending_event(self, thread_id: str) -> dict[str, Any] | None:
        snapshot = await self.graph.aget_state({"configurable": {"thread_id": thread_id}})
        pending = (snapshot.values or {}).get("pending")
        return pending["event"] if pending else None

    # ---------- graph ----------
    def _build_graph(self, checkpointer):
        g = StateGraph(AgentState)
        g.add_node("intake", self.intake)
        g.add_node("understand", self.understand)
        g.add_node("run_tools", self.run_tools)
        g.add_node("respond", self.respond)
        g.add_node("announce", self.announce)
        g.add_node("confirm_execute", self.confirm_execute)

        g.add_edge(START, "intake")
        g.add_conditional_edges(
            "intake",
            lambda s: s["route"],
            {"duplicate": END, "decision": "confirm_execute", "message": "understand"},
        )
        g.add_conditional_edges("understand", self._after_understand, {"tools": "run_tools", "end": END})
        g.add_conditional_edges(
            "run_tools",
            lambda s: "respond" if s.get("needs_summary") else "announce",
            {"respond": "respond", "announce": "announce"},
        )
        g.add_edge("respond", "announce")
        g.add_edge("announce", END)
        g.add_edge("confirm_execute", END)
        return g.compile(checkpointer=checkpointer)

    def _history(self, state: AgentState):
        return trim_messages(
            state["messages"],
            max_tokens=self.history_messages,
            strategy="last",
            token_counter=len,  # counts messages
            start_on="human",
            include_system=False,
        )

    # ---------- nodes ----------
    async def intake(self, state: AgentState) -> dict:
        request_id = state.get("request_id")
        last_id = state.get("last_request_id")
        if request_id and request_id == last_id and state.get("completed"):
            return {"route": "duplicate"}  # retry of a finished request: replay stored events
        is_retry = bool(request_id) and request_id == last_id

        update: dict[str, Any] = {
            "last_request_id": request_id,
            "completed": False,
            "events": [],
            "deferred": [],
            "needs_summary": False,
        }
        pending = state.get("pending")
        if state.get("decision"):
            return {**update, "route": "decision"}

        text = (state.get("user_message") or "").strip()
        word = text.lower().strip(" .!?")
        if pending and word in CONFIRM_WORDS:
            return {**update, "route": "decision", "decision": "confirm", "decision_operation_id": pending["operation_id"]}
        if pending and word in CANCEL_WORDS:
            return {**update, "route": "decision", "decision": "cancel", "decision_operation_id": pending["operation_id"]}

        update["route"] = "message"
        if pending:  # anything else replaces the pending operation
            update["pending"] = None
            update["events"] = [
                _event(
                    "operation_cancelled",
                    "I dropped the earlier request that was waiting for confirmation. Nothing was changed.",
                    operation_id=pending["operation_id"],
                )
            ]
        if not is_retry:
            update["messages"] = [HumanMessage(content=text)]
        return update

    async def understand(self, state: AgentState) -> dict:
        system = system_prompt(datetime.now(timezone.utc).date().isoformat())
        system += clarification_context(state.get("clarification"))
        try:
            ai = await self.llm.ainvoke([SystemMessage(content=system), *self._history(state)])
        except Exception:
            logger.exception("LLM call failed")
            # completed stays False so the client can retry the same request_id
            return {"events": [_event("error", "The assistant is temporarily unavailable. Please try again.", data={"code": "llm_unavailable"})]}
        if ai.tool_calls:
            return {"messages": [ai], "clarification": None}
        text = _text(ai) or "I'm not sure how to help with that. Could you rephrase?"
        return {
            "messages": [AIMessage(content=text)],
            "events": [_event("assistant_message", text)],
            "clarification": None,
            "completed": True,
        }

    @staticmethod
    def _after_understand(state: AgentState) -> str:
        last = state["messages"][-1]
        if isinstance(last, AIMessage) and last.tool_calls and not state.get("completed"):
            return "tools"
        return "end"

    async def _run_one(self, call: dict) -> dict:
        name, raw = call["name"], call.get("args") or {}
        try:
            if name in tools.IMMEDIATE_TOOLS:
                schema, func = tools.IMMEDIATE_TOOLS[name]
                data = await asyncio.to_thread(func, self.ctx, schema.model_validate(raw))
                return {"kind": "result", "data": data}
            if name in tools.PREPARED_TOOLS:
                schema, func = tools.PREPARED_TOOLS[name]
                data = await asyncio.to_thread(func, self.ctx, schema.model_validate(raw))
                return {"kind": "prepared", "data": data, "args": raw}
            return {"kind": "result", "data": {"ok": False, "error": f"Unknown tool {name}."}}
        except ValidationError as exc:
            return {"kind": "result", "data": {"ok": False, "error": f"Invalid arguments: {tools.first_error(exc)}"}}
        except Exception:
            logger.exception("Tool %s failed", name)
            return {"kind": "result", "data": {"ok": False, "error": "The operation failed unexpectedly."}}

    async def run_tools(self, state: AgentState) -> dict:
        ai = state["messages"][-1]
        events = list(state.get("events", []))
        entries = [(call, await self._run_one(call)) for call in ai.tool_calls]

        steps: list[dict] = []
        ambiguous: dict | None = None
        needs_summary = False
        for call, out in entries:
            if out["kind"] == "result":
                needs_summary = True
                events.append(_event("tool_status", f'{call["name"]} finished', data={"tool": call["name"], "ok": bool(out["data"].get("ok"))}))
                continue
            data = out["data"]
            if data["status"] == "step":
                steps.append(data["step"])
            elif data["status"] == "ambiguous":
                if ambiguous is None:
                    ambiguous = {
                        "operation": call["name"],
                        "args": out["args"],
                        "target": out["args"].get("target"),
                        "candidates": data["candidates"],
                    }
            else:
                needs_summary = True  # not found / invalid / no-op / search error

        tool_messages = []
        for call, out in entries:
            if out["kind"] == "result":
                content = json.dumps(out["data"], default=str)
            else:
                status = out["data"]["status"]
                if status == "step":
                    content = (
                        "Not queued yet: waiting for the user to clarify another task."
                        if ambiguous
                        else "Queued for user confirmation. The application will ask the user and perform it; do not say it is done."
                    )
                elif status == "ambiguous":
                    content = "Needs clarification: the user is being asked which task is meant."
                else:
                    content = json.dumps({"ok": False, "error": out["data"]["message"]})
            tool_messages.append(ToolMessage(content=content, tool_call_id=call["id"], name=call["name"]))

        deferred: list[dict] = []
        pending = None
        clarification = None
        if ambiguous:
            clarification = ambiguous
            deferred.append(
                _event("clarification_request", _clarification_text(ambiguous), operation=ambiguous["operation"], data={"candidates": ambiguous["candidates"]})
            )
        elif steps:
            steps = tools.merge_steps(steps)
            operation_id = uuid.uuid4().hex
            actions = {s["action"] for s in steps}
            operation = f"{actions.pop()}_task" if len(actions) == 1 else "multiple_operations"
            event = _event(
                "confirmation_required",
                _confirmation_text(steps),
                operation=operation,
                operation_id=operation_id,
                data={"steps": [{k: s[k] for k in ("action", "task_id", "task_title", "summary")} for s in steps]},
            )
            pending = {"operation_id": operation_id, "steps": steps, "event": event}
            deferred.append(event)

        return {
            "messages": tool_messages,
            "events": events,
            "deferred": deferred,
            "pending": pending,
            "clarification": clarification,
            "needs_summary": needs_summary,
        }

    async def respond(self, state: AgentState) -> dict:
        system = system_prompt(datetime.now(timezone.utc).date().isoformat()) + RESPONSE_SUFFIX
        text = ""
        try:
            ai = await self.llm.ainvoke([SystemMessage(content=system), *self._history(state)])
            text = _text(ai)
        except Exception:
            logger.exception("LLM summary failed; using fallback text")
        # Never fail here: tools may already have changed data.
        text = text or self._fallback_summary(state)
        return {"events": [*state.get("events", []), _event("assistant_message", text)]}

    @staticmethod
    def _fallback_summary(state: AgentState) -> str:
        lines = []
        for m in reversed(state["messages"]):
            if isinstance(m, HumanMessage):
                break
            if not isinstance(m, ToolMessage):
                continue
            try:
                data = json.loads(m.content)
            except ValueError:
                continue
            if not isinstance(data, dict):
                continue
            if data.get("ok") is False:
                lines.append(data.get("error", "An operation failed."))
            elif "task" in data:
                verb = "Created" if m.name == "create_task" else "Found"
                lines.append(f'{verb} task "{data["task"]["title"]}" (#{data["task"]["id"]}).')
            elif "count" in data:
                lines.append(f'Found {data["count"]} task(s).')
        return "\n".join(reversed(lines)) or "Done."

    async def announce(self, state: AgentState) -> dict:
        events = [*state.get("events", []), *state.get("deferred", [])]
        texts = [e["message"] for e in events if e["type"] in ("assistant_message", "confirmation_required", "clarification_request")]
        return {
            "events": events,
            "deferred": [],
            "completed": True,
            "messages": [AIMessage(content="\n\n".join(texts) or "Done.")],
        }

    async def confirm_execute(self, state: AgentState) -> dict:
        pending = state.get("pending")
        operation_id = state.get("decision_operation_id")
        if not pending or pending["operation_id"] != operation_id:
            return {
                "events": [
                    _event(
                        "operation_error",
                        "There is no matching pending operation. It may have been replaced or already handled.",
                        operation_id=operation_id,
                        data={"code": "no_pending_operation"},
                    )
                ],
                "completed": True,
            }
        if state.get("decision") == "cancel":
            text = "Okay, I cancelled that. No changes were made."
            return {
                "pending": None,
                "events": [_event("operation_cancelled", text, operation_id=operation_id)],
                "messages": [AIMessage(content=text)],
                "completed": True,
            }

        events: list[dict] = []
        lines: list[str] = []
        for step in pending["steps"]:
            try:
                result = await asyncio.to_thread(tools.execute_step, self.ctx, step)
            except Exception:
                logger.exception("Step failed: %s", step.get("summary"))
                result = {"ok": False, "message": f'Could not apply the change to "{step["task_title"]}" because of an unexpected error.'}
            lines.append(("Done: " if result["ok"] else "Failed: ") + result["message"])
            events.append(
                _event(
                    "operation_success" if result["ok"] else "operation_error",
                    result["message"],
                    operation_id=operation_id,
                    operation=f'{step["action"]}_task',
                    data=result.get("data"),
                )
            )
        summary = "\n".join(lines)
        events.append(_event("assistant_message", summary))
        return {"pending": None, "events": events, "messages": [AIMessage(content=summary)], "completed": True}