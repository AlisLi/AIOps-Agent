from aiops.core.types import QueryCategory
from aiops.rag.router import RuleRouter


def test_resource_alert():
    r = RuleRouter()
    assert r.classify("CPU usage 超过 90%") is QueryCategory.RESOURCE_ALERT


def test_log_error():
    r = RuleRouter()
    assert r.classify("看到 Exception Traceback 怎么办?") is QueryCategory.LOG_ERROR


def test_qa():
    r = RuleRouter()
    assert r.classify("介绍一下这个项目的架构") is QueryCategory.QA
