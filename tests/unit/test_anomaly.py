import pytest

from aiops.monitor.metrics_detector import AnomalyDetector


def test_three_sigma_triggers_on_spike():
    d = AnomalyDetector(window=60)
    for _ in range(60):
        d.observe(40.0)
    is_anom, tag = d.vote(95.0)
    assert is_anom
    assert tag in ("3sigma", "ewma", "vote")


def test_normal_range_no_alert():
    d = AnomalyDetector(window=60)
    for _ in range(60):
        d.observe(40.0)
    is_anom, _ = d.vote(41.0)
    assert not is_anom
