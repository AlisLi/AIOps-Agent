"""Root cause analyzer: topology + RAG + LLM."""
from __future__ import annotations

import json
from pathlib import Path

from jinja2 import Template

from aiops.core.logging import log
from aiops.core.types import AlertEvent, QueryCategory, RAGRequest, RCAResult
from aiops.llm.client import get_llm
from aiops.rag.pipeline import get_pipeline
from aiops.rca.graph_client import get_neo4j

ROOT = Path(__file__).resolve().parents[3]
TPL = ROOT / "configs" / "prompts" / "rca.jinja"


class RCAAnalyzer:
    def __init__(self) -> None:
        self.graph = get_neo4j()
        self.rag = get_pipeline()
        self.llm = get_llm()

    def _build_query(self, alert: AlertEvent, subgraph: list[dict]) -> str:
        neighbors = ", ".join(f"{n['kind']}:{n['name']}" for n in subgraph)
        return (
            f"服务 {alert.service} 指标 {alert.metric} 当前值 {alert.value} "
            f"超过阈值 {alert.threshold}。上下游: {neighbors}。可能根因？"
        )

    async def analyze(self, alert: AlertEvent) -> RCAResult:
        with log.contextualize(trace_id=alert.alert_id):
            subgraph = self.graph.neighbors(alert.service)
            cat = QueryCategory.LOG_ERROR if alert.detected_by == "regex" else QueryCategory.RESOURCE_ALERT
            rag_resp = await self.rag.run(
                RAGRequest(trace_id=alert.alert_id, query=self._build_query(alert, subgraph), category=cat)
            )
            tpl = Template(TPL.read_text(encoding="utf-8"))
            prompt = tpl.render(alert=alert.model_dump(), subgraph=subgraph, docs=rag_resp.docs)
            text = await self.llm.ainvoke(prompt, temperature=0.1)
            parsed = self._parse_json(text, alert)
            return RCAResult(
                alert_id=alert.alert_id,
                root_cause_service=parsed.get("root_cause_service", alert.service),
                reasoning=parsed.get("reasoning", text[:500]),
                evidence=rag_resp.docs,
                suggested_actions=parsed.get("suggested_actions", []),
            )

    @staticmethod
    def _parse_json(text: str, alert: AlertEvent) -> dict:
        # Try to find the first JSON object in the text.
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except Exception:
                pass
        return {
            "root_cause_service": alert.service,
            "reasoning": text[:300],
            "suggested_actions": ["restart_pod"],
        }
