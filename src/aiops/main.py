"""FastAPI entry point — REST + SSE."""
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from aiops.agents.heal_agent import HealAgent
from aiops.agents.monitor_agent import MonitorAgent
from aiops.agents.qa_agent import QAAgent
from aiops.agents.rag_agent import RAGAgent
from aiops.agents.rca_agent import RCAAgent
from aiops.bus.kafka_producer import KafkaProducer
from aiops.bus.topics import Topic
from aiops.core.logging import log
from aiops.core.types import AlertEvent


class ChatRequest(BaseModel):
    session_id: str
    user_id: str
    query: str
    stream: bool = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("bootstrapping agents ...")
    app.state.qa = QAAgent()
    app.state.rag = RAGAgent()
    app.state.monitor = MonitorAgent()
    app.state.rca = RCAAgent()
    app.state.heal = HealAgent()

    # fire-and-forget starts (don't block if kafka is down)
    for a in (app.state.rag, app.state.rca, app.state.heal, app.state.qa):
        await a.start()
    await app.state.monitor.start()
    log.info("agents ready")
    try:
        yield
    finally:
        log.info("shutting down ...")
        for a in (app.state.rag, app.state.rca, app.state.heal, app.state.qa):
            await a.stop()
        await app.state.monitor.stop()


app = FastAPI(title="AIOps-Agent", lifespan=lifespan)


@app.get("/health")
async def health() -> dict:
    deps: dict[str, str] = {}
    try:
        import redis  # type: ignore
        from aiops.core.config import settings
        redis.Redis.from_url(settings.redis.url).ping()
        deps["redis"] = "ok"
    except Exception as e:
        deps["redis"] = f"fail:{e}"
    try:
        from aiops.rca.graph_client import get_neo4j
        nc = get_neo4j()
        deps["neo4j"] = "ok" if nc._driver is not None else "mock"
    except Exception as e:
        deps["neo4j"] = f"fail:{e}"
    try:
        from aiops.rag.retriever_vector import get_vector_retriever
        vr = get_vector_retriever()
        deps["milvus"] = "ok" if vr._use_milvus else "local"
    except Exception as e:
        deps["milvus"] = f"fail:{e}"
    try:
        _ = KafkaProducer.get()
        deps["kafka"] = "ok"
    except Exception as e:
        deps["kafka"] = f"fail:{e}"
    return {"status": "ok", "deps": deps}


@app.post("/chat")
async def chat(req: ChatRequest):
    trace_id = str(uuid.uuid4())
    qa: QAAgent = app.state.qa

    if not req.stream:
        resp = await qa.answer(
            session_id=req.session_id, user_id=req.user_id, query=req.query, trace_id=trace_id
        )
        return resp.model_dump()

    async def sse():
        resp = await qa.answer(
            session_id=req.session_id, user_id=req.user_id, query=req.query, trace_id=trace_id
        )
        # Minimal SSE: a few chunks then done (true streaming LLM stream plumbing is optional)
        import json
        for chunk in resp.answer.split():
            yield f"event: token\ndata: {json.dumps({'delta': chunk + ' '}, ensure_ascii=False)}\n\n"
        yield f"event: done\ndata: {json.dumps({'trace_id': resp.trace_id, 'docs': [d.model_dump() for d in resp.docs]}, ensure_ascii=False)}\n\n"

    return StreamingResponse(sse(), media_type="text/event-stream")


@app.post("/alert")
async def post_alert(alert: AlertEvent):
    try:
        prod = KafkaProducer.get()
        await prod.send(Topic.ALERT_RAW, key=alert.alert_id, payload=alert.model_dump(mode="json"))
        return {"accepted": True, "alert_id": alert.alert_id}
    except Exception as e:
        # fall back: analyze in-process
        from aiops.rca.analyzer import RCAAnalyzer
        result = await RCAAnalyzer().analyze(alert)
        raise HTTPException(status_code=202, detail={"kafka_fail": str(e), "inline_rca": result.model_dump()})
