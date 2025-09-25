import json
from pathlib import Path

from modules.budget import load_budget, get_latest_metrics
from modules.utils import history_file_path


def test_load_budget_ok(tmp_path, monkeypatch):
    data = [{"domain": "example.com", "budget": {"LCP": 2}}]
    (tmp_path / "domain.json").write_text(json.dumps(data, ensure_ascii=False))
    monkeypatch.setenv("POLZA_DATA_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    assert load_budget() == data


def test_load_budget_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("POLZA_DATA_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    assert load_budget() == []


def test_get_latest_metrics(tmp_path, monkeypatch):
    monkeypatch.setenv("POLZA_DATA_DIR", str(tmp_path))
    history_path = Path(history_file_path("https://example.com"))
    history_path.parent.mkdir(parents=True, exist_ok=True)
    history_data = [{"metrics": {"LCP": "2.5 s", "TBT": "100 ms", "TTFB": "Root document took 50 ms"}}]
    history_path.write_text(json.dumps(history_data, ensure_ascii=False))
    monkeypatch.chdir(tmp_path)
    metrics = get_latest_metrics("https://example.com")
    assert metrics == {"LCP": 2.5, "TBT": 0.1, "TTFB": 0.05}


def test_get_latest_metrics_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("POLZA_DATA_DIR", str(tmp_path))
    (tmp_path / "history_files").mkdir()
    monkeypatch.chdir(tmp_path)
    assert get_latest_metrics("https://missing.com") == {}

