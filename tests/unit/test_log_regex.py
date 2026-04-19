from aiops.monitor.log_detector import LogRegexDetector


def test_regex_match():
    d = LogRegexDetector()
    events = d.scan(["2026 INFO ok", "2026 ERROR OutOfMemoryError worker"], service="svc")
    assert len(events) >= 1
    assert events[0].metric == "log_error"
    assert events[0].detected_by == "regex"
