"""Lightweight offline metrics: hallucination, answer accuracy, recall@k."""
from __future__ import annotations

from typing import Iterable


def _tokens(s: str) -> set[str]:
    return {t.lower() for t in s.split() if t.strip()}


def hallucination_rate(answers: list[str], contexts: list[list[str]]) -> float:
    """Fraction of answers whose token-overlap with their context < 0.1."""
    if not answers:
        return 0.0
    bad = 0
    for a, ctx in zip(answers, contexts):
        ctx_tokens = set().union(*(_tokens(c) for c in ctx)) if ctx else set()
        ans_tokens = _tokens(a)
        if not ans_tokens:
            continue
        overlap = len(ans_tokens & ctx_tokens) / max(len(ans_tokens), 1)
        if overlap < 0.1:
            bad += 1
    return bad / len(answers)


def answer_accuracy(preds: list[str], golds: list[str]) -> float:
    if not preds:
        return 0.0
    hits = sum(1 for p, g in zip(preds, golds) if _tokens(g).issubset(_tokens(p)))
    return hits / len(preds)


def recall_at_k(retrieved_ids: list[list[str]], relevant_ids: list[set[str]], k: int = 5) -> float:
    if not retrieved_ids:
        return 0.0
    total = 0.0
    for retr, rel in zip(retrieved_ids, relevant_ids):
        if not rel:
            continue
        hits = len(set(retr[:k]) & rel)
        total += hits / len(rel)
    return total / len(retrieved_ids)


def mrr(retrieved_ids: list[list[str]], relevant_ids: list[set[str]]) -> float:
    if not retrieved_ids:
        return 0.0
    total = 0.0
    for retr, rel in zip(retrieved_ids, relevant_ids):
        for idx, r in enumerate(retr, start=1):
            if r in rel:
                total += 1.0 / idx
                break
    return total / len(retrieved_ids)
