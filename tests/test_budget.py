import json
from modules.budget import load_budget, get_latest_metrics


def test_load_budget_ok(tmp_path, monkeypatch):
    data = [{"domain": "example.com", "budget": {"LCP": 2}}]
    (tmp_path / "domain.json").write_text(json.dumps(data, ensure_ascii=False))
    monkeypatch.chdir(tmp_path)
    assert load_budget() == data


def test_load_budget_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert load_budget() == []


def test_get_latest_metrics(tmp_path, monkeypatch):
    history_dir = tmp_path / "history_files"
    history_dir.mkdir()
    history_data = [{"metrics": {"LCP": "2.5 s", "TBT": "100 ms", "TTFB": "Root document took 50 ms"}}]
    (history_dir / "history_example.com.json").write_text(json.dumps(history_data, ensure_ascii=False))
    monkeypatch.chdir(tmp_path)
    metrics = get_latest_metrics("https://example.com")
    assert metrics == {"LCP": 2.5, "TBT": 0.1, "TTFB": 0.05}


def test_get_latest_metrics_missing(tmp_path, monkeypatch):
    (tmp_path / "history_files").mkdir()
    monkeypatch.chdir(tmp_path)
    assert get_latest_metrics("https://missing.com") == {}
