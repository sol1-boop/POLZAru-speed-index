from modules.metrics import parse_metric


def test_parse_metric_seconds():
    assert parse_metric("1.5 s") == 1.5


def test_parse_metric_ms_to_s():
    assert parse_metric("1500 ms", unit="s") == 1.5


def test_parse_metric_s_to_ms():
    assert parse_metric("1.5 s", unit="ms") == 1500
