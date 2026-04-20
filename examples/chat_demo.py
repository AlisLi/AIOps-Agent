"""Chat demo — uses QAAgent directly, no Kafka required.

Run:
    # optional: seed the in-process KB
    python scripts/seed_knowledge.py

    python examples/chat_demo.py
"""
from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path

# 让 `scripts` 和 `src/aiops` 都能被直接 `python examples/xxx.py` 找到
_ROOT = Path(__file__).resolve().parent.parent
for p in (_ROOT, _ROOT / "src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from aiops.agents.qa_agent import QAAgent  # noqa: E402
from scripts.seed_knowledge import main as seed  # noqa: E402


async def main() -> None:
    seed()
    agent = QAAgent()

    session_id = "demo-sess"
    user_id = "demo-user"
    queries = [
        "芯片缺陷系统 chip-api 的 CPU 飙高，先查哪里？",
        "OutOfMemoryError 在 chip-worker，怎么办？",
        "帮我回忆一下我们刚才讨论的第一个问题。",
    ]
    for q in queries:
        resp = await agent.answer(
            session_id=session_id, user_id=user_id, query=q, trace_id=str(uuid.uuid4())
        )
        print("=" * 60)
        print(f"Q: {q}")
        print(f"A: {resp.answer}")
        print(f"Retrieved: {[d.doc_id for d in resp.docs]}")


if __name__ == "__main__":
    asyncio.run(main())
