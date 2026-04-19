"""Runbook executor. For safety, only runs commands in a dedicated mock/shell allowlist."""
from __future__ import annotations

import asyncio
import shlex
from typing import Any

from jinja2 import Template

from aiops.core.logging import log
from aiops.core.types import HealRequest, HealResult
from aiops.heal.runbook_loader import load_runbook


class RunbookExecutor:
    async def _run_shell(self, cmd: str) -> tuple[int, str]:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        out, _ = await proc.communicate()
        return proc.returncode or 0, out.decode(errors="ignore")

    async def execute(self, req: HealRequest) -> HealResult:
        logs: list[str] = []
        try:
            book = load_runbook(req.runbook)
        except Exception as e:
            return HealResult(alert_id=req.alert_id, runbook=req.runbook, success=False, logs=[str(e)])

        success = True
        for step in book.get("steps", []):
            step_id = step.get("id", "?")
            stype = step.get("type", "shell")
            cmd_tpl = step.get("cmd", "")
            cmd = Template(cmd_tpl).render(**req.params)
            logs.append(f"[{step_id}] ({stype}) $ {cmd}")
            if stype == "shell":
                # safe path: only mocked commands (echo) by default
                if not cmd.strip().startswith("echo"):
                    logs.append(f"[{step_id}] blocked non-mock command, skipped")
                    continue
                rc, out = await self._run_shell(cmd)
                logs.append(out.strip())
                if rc != 0:
                    success = False
                    break
            else:
                logs.append(f"[{step_id}] unsupported type: {stype}")
        log.info(f"runbook {req.runbook} done success={success}")
        return HealResult(alert_id=req.alert_id, runbook=req.runbook, success=success, logs=logs)


_exec: RunbookExecutor | None = None


def get_executor() -> RunbookExecutor:
    global _exec
    if _exec is None:
        _exec = RunbookExecutor()
    return _exec
