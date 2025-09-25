import pytest

from modules import metrics


def make_entry(timestamp, speed_index, lcp=None, fcp=None, ttfb=None, tbt=None):
    return {
        "timestamp": timestamp,
        "metrics": {
            "Speed Index": f"{speed_index} s" if speed_index is not None else None,
            "LCP": f"{(lcp if lcp is not None else speed_index)} s" if lcp is not None else (f"{speed_index} s" if speed_index is not None else None),
            "FCP": f"{(fcp if fcp is not None else speed_index)} s" if fcp is not None else (f"{speed_index} s" if speed_index is not None else None),
            "TTFB": f"{(ttfb if ttfb is not None else 0.4) * 1000} ms" if ttfb is not None else "400 ms",
            "TBT": f"{(tbt if tbt is not None else 0.2) * 1000} ms" if tbt is not None else "200 ms",
        },
    }


@pytest.fixture
def sample_domains():
    return [
        {"domain": "stable.test", "budget": {"Speed Index": 4, "LCP": 3}},
        {"domain": "problem.test", "budget": {"Speed Index": 3, "LCP": 2}},
        {"domain": "improved.test", "budget": {"Speed Index": 6}},
    ]


def test_build_domain_overview_segments(monkeypatch, sample_domains):
    history_map = {
        "stable.test": [
            make_entry("2024-05-01T10:00:00", 3.2, lcp=2.4),
            make_entry("2024-05-05T10:00:00", 3.1, lcp=2.3),
        ],
        "problem.test": [
            make_entry("2024-05-01T10:00:00", 4.8, lcp=4.5),
            make_entry("2024-05-05T10:00:00", 5.1, lcp=4.6),
        ],
        "improved.test": [
            make_entry("2024-05-01T10:00:00", 7.0, lcp=5.5),
            make_entry("2024-05-05T10:00:00", 5.0, lcp=4.0),
        ],
    }

    monkeypatch.setattr(metrics, "load_history", lambda domain: history_map.get(domain, []))

    overview = metrics.build_domain_overview(sample_domains, history_limit=None)
    assert len(overview) == 3

    stable = next(item for item in overview if item["domain"] == "stable.test")
    problem = next(item for item in overview if item["domain"] == "problem.test")
    improved = next(item for item in overview if item["domain"] == "improved.test")

    assert stable["segment"] == "all"
    assert stable["status_level"] == "neutral"
    assert problem["segment"] == "problem"
    assert problem["status_level"] == "critical"
    assert improved["segment"] == "improved"
    assert improved["status_level"] == "positive"

    assert pytest.approx(problem["trend_value"], 0.01) == 0.3
    assert improved["trend_value"] < 0
    assert len(improved["sparkline"]) == 2


def test_build_domain_overview_handles_missing_data(monkeypatch):
    domains = [{"domain": "empty.test", "budget": {}}]
    monkeypatch.setattr(metrics, "load_history", lambda domain: [])

    overview = metrics.build_domain_overview(domains)
    assert overview == [
        {
            "domain": "empty.test",
            "segment": "all",
            "status_level": "neutral",
            "last_updated": None,
            "metrics": {},
            "trend_value": None,
            "trend_percent": None,
            "sparkline": [],
        }
    ]
