from modules.metrics import summarize_history


def test_summarize_history():
    history = [
        {'metrics': {'FCP': '1 s', 'LCP': '2 s', 'TTFB': '100 ms', 'TBT': '50 ms'}},
        {'metrics': {'FCP': '2 s', 'LCP': '4 s', 'TTFB': '300 ms', 'TBT': '150 ms'}},
    ]
    stats = summarize_history(history)
    assert stats['FCP']['min'] == 1
    assert stats['FCP']['max'] == 2
    assert round(stats['FCP']['avg'], 2) == 1.5


def test_summarize_history_empty():
    stats = summarize_history([])
    assert stats == {'FCP': None, 'LCP': None, 'TTFB': None, 'TBT': None}
