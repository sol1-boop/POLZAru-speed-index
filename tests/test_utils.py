import json
import pytest
from modules.config import get_telegram_settings


def test_get_telegram_settings_ok(tmp_path, monkeypatch):
    cfg = {"telegram_token": "t", "channel_id": 1}
    (tmp_path / "config.json").write_text(json.dumps(cfg, ensure_ascii=False))
    monkeypatch.chdir(tmp_path)
    assert get_telegram_settings() == ("t", 1)


def test_get_telegram_settings_missing(tmp_path, monkeypatch):
    (tmp_path / "config.json").write_text("{}")
    monkeypatch.chdir(tmp_path)
    with pytest.raises(KeyError):
        get_telegram_settings()
