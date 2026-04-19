"""Rule-based query classifier."""
from __future__ import annotations

import re

from aiops.core.types import QueryCategory

_RE_RESOURCE = re.compile(r"(CPU|Memory|内存|Disk|磁盘|IO|延迟|latency|TPS|QPS|超过|阈值)", re.I)
_RE_LOG = re.compile(r"(ERROR|Exception|Traceback|堆栈|日志|panic|fatal|OOM)", re.I)


class RuleRouter:
    def classify(self, query: str) -> QueryCategory:
        if _RE_RESOURCE.search(query):
            return QueryCategory.RESOURCE_ALERT
        if _RE_LOG.search(query):
            return QueryCategory.LOG_ERROR
        return QueryCategory.QA
