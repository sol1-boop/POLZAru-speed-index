
import json
from modules.alerts import check_exceedances


def _write_domain(tmp_path, domain, budget=None):
    data = [{"domain": domain, "budget": budget or {}}]
    (tmp_path / "domain.json").write_text(json.dumps(data, ensure_ascii=False))


def _write_history(tmp_path, domain, metrics):
    (tmp_path / "history_files").mkdir()
    history = [{"timestamp": "2024-01-01", "metrics": metrics}]
    path = tmp_path / "history_files" / f"history_{domain}.json"
    path.write_text(json.dumps(history, ensure_ascii=False))


def test_check_exceedances(tmp_path, monkeypatch):
    domain = "example.com"
    _write_domain(tmp_path, domain, {"FCP": 1})
    _write_history(tmp_path, domain, {"FCP": "2 s"})
    monkeypatch.chdir(tmp_path)
    exceeded = check_exceedances()
    assert exceeded and exceeded[0]["domain"] == domain
    assert "FCP" in exceeded[0]["exceeded_metrics"]

