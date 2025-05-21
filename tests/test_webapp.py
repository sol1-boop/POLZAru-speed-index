import json
import pytest

from webapp import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "history_files").mkdir()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def write_history(tmp_path, domain, metrics):
    history = [{"timestamp": "2024-01-01", "metrics": metrics}]
    filename = f"history_{domain}.json"
    path = tmp_path / "history_files" / filename
    path.write_text(json.dumps(history, ensure_ascii=False))


def write_domain(tmp_path, domain, budget=None):
    data = [{"domain": domain, "budget": budget or {}}]
    (tmp_path / "domain.json").write_text(json.dumps(data, ensure_ascii=False))


def test_index_ok(client, tmp_path):
    write_domain(tmp_path, "example.com")
    rv = client.get("/")
    assert rv.status_code == 200


def test_get_stats_success(client, tmp_path):
    domain = "example.com"
    write_domain(tmp_path, domain)
    metrics = {"FCP": "1 s", "LCP": "2 s", "TTFB": "100 ms", "TBT": "50 ms"}
    write_history(tmp_path, domain, metrics)

    rv = client.get("/get_stats", query_string={"domain": domain})
    assert rv.status_code == 200
    data = rv.get_json()
    assert data["metrics"]["FCP"] == [1.0]


def test_get_stats_missing_domain(client):
    rv = client.get("/get_stats")
    assert rv.status_code == 400


def test_get_stats_invalid_domain(client, tmp_path):
    write_domain(tmp_path, "example.com")
    rv = client.get("/get_stats", query_string={"domain": "invalid.com"})
    assert rv.status_code == 404


def test_check_metrics_exceeded(client, tmp_path):
    domain = "example.com"
    write_domain(tmp_path, domain, {"FCP": 1})
    metrics = {"FCP": "2 s"}
    write_history(tmp_path, domain, metrics)

    rv = client.get("/check_metrics")
    assert rv.status_code == 404
    data = rv.get_json()
    assert data["status"] == "EXCEEDED"


def test_check_metrics_ok(client, tmp_path):
    domain = "example.com"
    write_domain(tmp_path, domain, {"FCP": 3})
    metrics = {"FCP": "2 s"}
    write_history(tmp_path, domain, metrics)

    rv = client.get("/check_metrics")
    assert rv.status_code == 200
    data = rv.get_json()
    assert data["status"] == "OK"


def test_check_metrics_new_metrics(client, tmp_path):
    domain = "example.com"
    write_domain(tmp_path, domain, {"INP": 0.2, "Speed Index": 2})
    metrics = {"INP": "250 ms", "Speed Index": "2.5 s"}
    write_history(tmp_path, domain, metrics)

    rv = client.get("/check_metrics")
    assert rv.status_code == 404
    data = rv.get_json()
    assert data["status"] == "EXCEEDED"
    assert data["details"][0]["exceeded_metrics"]["INP"]["actual"] == 0.25
