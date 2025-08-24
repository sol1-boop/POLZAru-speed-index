from modules.metrics import (
    calculate_stats_for_metrics,
    compute_domain_stats,
    summarize_history,
)


def test_summarize_history():
    history = [
        {
            "metrics": {
                "FCP": "1 s",
                "LCP": "2 s",
                "TTFB": "100 ms",
                "TBT": "50 ms",
                "Speed Index": "1.0 s",
            }
        },
        {
            "metrics": {
                "FCP": "2 s",
                "LCP": "4 s",
                "TTFB": "300 ms",
                "TBT": "150 ms",
                "Speed Index": "2.0 s",
            }
        },
    ]
    stats = summarize_history(history)
    assert stats["FCP"]["min"] == 1
    assert stats["FCP"]["max"] == 2
    assert round(stats["FCP"]["avg"], 2) == 1.5


def test_summarize_history_empty():
    stats = summarize_history([])
    assert stats == {
        "FCP": None,
        "LCP": None,
        "TTFB": None,
        "TBT": None,
        "Speed Index": None,
    }


def test_calculate_stats_for_metrics():
    fcp = [1, 2, 3]
    lcp = [2, 4, 6]
    ttfb = [0.1, 0.2, 0.3]
    tbt = [0.05, 0.1, 0.15]
    si = [1, 2, 3]

    stats = calculate_stats_for_metrics(fcp, lcp, ttfb, tbt, si)
    assert stats["FCP"]["min"] == 1
    assert stats["FCP"]["max"] == 3
    assert stats["LCP"]["median"] == 4


def test_calculate_stats_single_value():
    stats = calculate_stats_for_metrics([1], [2], [0.1], [0.05], [1.0])
    assert stats["FCP"]["percentile_75"] is None
    assert stats["LCP"]["percentile_95"] is None


def test_calculate_stats_for_metrics_empty_values():
    stats = calculate_stats_for_metrics([], [], [], [])
    assert stats["FCP"]["percentile_75"] is None
    assert stats["FCP"]["median"] is None
    assert stats["FCP"]["max"] is None
    assert stats["FCP"]["min"] is None


def test_compute_domain_stats():
    history = [
        {
            "timestamp": "t1",
            "metrics": {
                "FCP": "1 s",
                "LCP": "2 s",
                "TTFB": "100 ms",
                "TBT": "50 ms",
                "Speed Index": "1.0 s",
            },
        },
        {
            "timestamp": "t2",
            "metrics": {
                "FCP": "2 s",
                "LCP": "4 s",
                "TTFB": "300 ms",
                "TBT": "150 ms",
                "Speed Index": "2.0 s",
            },
        },
    ]
    result = compute_domain_stats(history)
    assert result["dates"] == ["t1", "t2"]
    assert result["metrics"]["TTFB"] == [0.1, 0.3]
    assert result["stats"]["FCP"]["max"] == 2

