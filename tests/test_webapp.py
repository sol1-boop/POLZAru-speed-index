import json

import pytest

from webapp import app
from modules.utils import history_file_path


@pytest.fixture
def client():
    app.config['TESTING'] = True
    return app.test_client()


def test_metrics_view_ok(tmp_path, monkeypatch, client):
    history_path = tmp_path / history_file_path('https://example.com')
    history_path.parent.mkdir()
    history_data = [{
        'timestamp': '2024-01-01',
        'metrics': {
            'FCP': '1 s',
            'LCP': '2 s',
            'TTFB': '100 ms',
            'TBT': '200 ms',
            'Speed Index': '3 s'
        }
    }]
    history_path.write_text(json.dumps(history_data, ensure_ascii=False))
    monkeypatch.chdir(tmp_path)
    response = client.get('/metrics', query_string={'url': 'https://example.com'})
    assert response.status_code == 200


def test_metrics_view_missing_domain(client):
    response = client.get('/metrics')
    assert response.status_code == 400
