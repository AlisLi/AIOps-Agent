"""QA Agent — LangGraph state machine wrapping memory + RAG + LLM."""
from __future__ import annotations

from pathlib import Path
from typing import TypedDict

from jinja2 import Template

from aiops.agents.base import AgentBase
from aiops.bus.topics import Topic
from aiops.core.logging import log
from aiops.core.types import (
    ChatMessage,
    QAResponse,
    QueryCategory,
    RAGRequest,
    RetrievedDoc,
)
from aiops.eval.tracer import Timer, get_tracer
from aiops.llm.client import get_llm
from aiops.memory.long_term import get_long_term
from aiops.memory.short_term import get_short_term
from aiops.rag.pipeline import get_pipeline
from aiops.rag.router import RuleRouter

ROOT = Path(__file__).resolve().parents[3]
QA_TPL = ROOT / "configs" / "prompts" / "qa.jinja"


class QAState(TypedDict, total=False):
    session_id: str
    user_id: str
    trace_id: str
    query: str
    category: QueryCategory
    short_summary: str
    short_recent: list[ChatMessage]
    long_facts: list[str]
    rag_docs: list[RetrievedDoc]
    answer: str


def build_graph():
    """Compile the QA LangGraph. Falls back to a plain async pipeline if LangGraph is unavailable."""
    router = RuleRouter()
    pipeline = get_pipeline()
    short = get_short_term()
    long_ = get_long_term()
    llm = get_llm()
    tracer = get_tracer()
    tpl = Template(QA_TPL.read_text(encoding="utf-8"))

    async def load_memory(state: QAState) -> QAState:
        summary, recent = await short.get_context(state["session_id"])
        facts = await long_.recall(state["user_id"], state["query"])
        return {**state, "short_summary": summary, "short_recent": recent, "long_facts": facts}

    async def classify(state: QAState) -> QAState:
        return {**state, "category": router.classify(state["query"])}

    async def retrieve(state: QAState) -> QAState:
        rag_resp = await pipeline.run(
            RAGRequest(trace_id=state["trace_id"], query=state["query"], category=state["category"])
        )
        return {**state, "rag_docs": rag_resp.docs}

    async def generate(state: QAState) -> QAState:
        prompt = tpl.render(
            summary=state.get("short_summary", ""),
            recent=[m.model_dump() for m in state.get("short_recent", [])],
            profile=state.get("long_facts", []),
            docs=state.get("rag_docs", []),
            query=state["query"],
        )
        with Timer() as t:
            answer = await llm.ainvoke(prompt)
        await tracer.emit(
            "qa.generate", state["trace_id"],
            {"query": state["query"]}, {"answer": answer[:300]}, t.elapsed_ms,
        )
        return {**state, "answer": answer}

    async def update_memory(state: QAState) -> QAState:
        await short.append(state["session_id"], ChatMessage(role="user", content=state["query"]))
        await short.append(state["session_id"], ChatMessage(role="assistant", content=state["answer"]))
        # fire-and-forget profile extraction
        import asyncio
        asyncio.create_task(long_.extract_and_store(state["user_id"], [
            ChatMessage(role="user", content=state["query"]),
            ChatMessage(role="assistant", content=state["answer"]),
        ]))
        return state

    try:
        from langgraph.graph import END, StateGraph  # type: ignore

        g = StateGraph(QAState)
        g.add_node("load_memory", load_memory)
        g.add_node("classify", classify)
        g.add_node("retrieve", retrieve)
        g.add_node("generate", generate)
        g.add_node("update_memory", update_memory)
        g.set_entry_point("load_memory")
        g.add_edge("load_memory", "classify")
        g.add_edge("classify", "retrieve")
        g.add_edge("retrieve", "generate")
        g.add_edge("generate", "update_memory")
        g.add_edge("update_memory", END)
        return g.compile()
    except Exception as e:
        log.warning(f"langgraph unavailable ({e}); using plain pipeline")

        class Fallback:
            async def ainvoke(self, state: QAState) -> QAState:
                s = await load_memory(state)
                s = await classify(s)
                s = await retrieve(s)
                s = await generate(s)
                s = await update_memory(s)
                return s

        return Fallback()


class QAAgent(AgentBase):
    name = "qa"
    topics = [Topic.QA_REQUEST]

    def __init__(self) -> None:
        super().__init__()
        self.graph = build_graph()

    async def answer(self, *, session_id: str, user_id: str, query: str, trace_id: str) -> QAResponse:
        state: QAState = {
            "session_id": session_id, "user_id": user_id, "query": query, "trace_id": trace_id,
        }
        result = await self.graph.ainvoke(state)
        return QAResponse(trace_id=trace_id, answer=result.get("answer", ""), docs=result.get("rag_docs", []))

    async def on_message(self, topic: str, payload: dict) -> None:
        resp = await self.answer(
            session_id=payload["session_id"],
            user_id=payload["user_id"],
            query=payload["query"],
            trace_id=payload["trace_id"],
        )
        if self.producer is not None:
            await self.producer.send(Topic.QA_RESPONSE, key=resp.trace_id, payload=resp.model_dump(mode="json"))
