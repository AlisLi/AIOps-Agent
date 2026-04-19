"""Kafka topic names."""
from enum import StrEnum


class Topic(StrEnum):
    QA_REQUEST = "qa.request"
    QA_RESPONSE = "qa.response"
    RAG_REQUEST = "rag.request"
    RAG_RESPONSE = "rag.response"
    ALERT_RAW = "alert.raw"
    RCA_REQUEST = "rca.request"
    RCA_RESULT = "rca.result"
    HEAL_REQUEST = "heal.request"
    HEAL_RESULT = "heal.result"
    EVAL_TRACE = "eval.trace"
