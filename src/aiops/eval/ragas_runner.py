"""RAGAS evaluation runner.

Usage:
    python -m aiops.eval.ragas_runner --dataset data/eval.jsonl

Dataset JSONL format per line:
    {"question": "...", "answer": "...", "contexts": ["..."], "ground_truth": "..."}
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from aiops.core.logging import log


def _load_jsonl(p: Path) -> list[dict]:
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    args = parser.parse_args()

    records = _load_jsonl(Path(args.dataset))
    log.info(f"loaded {len(records)} eval records")

    try:
        from ragas import evaluate  # type: ignore
        from ragas.metrics import answer_relevancy, context_precision, context_recall, faithfulness
        from datasets import Dataset
    except Exception as e:
        log.warning(f"RAGAS unavailable ({e}); falling back to lightweight offline metrics")
        from aiops.eval.metrics import hallucination_rate
        hr = hallucination_rate(
            [r.get("answer", "") for r in records],
            [r.get("contexts", []) for r in records],
        )
        print(json.dumps({"hallucination_rate_fallback": hr}, ensure_ascii=False, indent=2))
        return

    ds = Dataset.from_list(records)
    result = evaluate(ds, metrics=[faithfulness, answer_relevancy, context_precision, context_recall])
    print(result)


if __name__ == "__main__":
    main()
