import json
from pathlib import Path
from uuid import uuid4

import pytest

from modules.config import get_telegram_settings
from modules.utils import get_storage_dir, load_domains


def test_get_telegram_settings_ok(tmp_path, monkeypatch):
    cfg = {"telegram_token": "t", "channel_id": 1}
    (tmp_path / "config.json").write_text(json.dumps(cfg, ensure_ascii=False))
    monkeypatch.setenv("POLZA_DATA_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    assert get_telegram_settings() == ("t", 1)


def test_get_telegram_settings_missing(tmp_path, monkeypatch):
    (tmp_path / "config.json").write_text("{}")
    monkeypatch.setenv("POLZA_DATA_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    with pytest.raises(KeyError):
        get_telegram_settings()


def test_get_storage_dir_expands_user_home(monkeypatch):
    unique_suffix = f"polza-data-{uuid4().hex}"
    monkeypatch.setenv("POLZA_DATA_DIR", f"~/{unique_suffix}")
    expected = Path.home() / unique_suffix
    assert get_storage_dir() == expected


def test_load_domains_discovers_parent_storage(tmp_path, monkeypatch):
    storage_dir = tmp_path / "storage"
    storage_dir.mkdir()
    domains = [{"domain": "https://example.com"}]
    (storage_dir / "domain.json").write_text(json.dumps(domains, ensure_ascii=False))

    nested = storage_dir / "nested" / "level"
    nested.mkdir(parents=True)

    monkeypatch.chdir(nested)
    monkeypatch.delenv("POLZA_DATA_DIR", raising=False)

    loaded = load_domains()
    assert loaded[0]["domain"] == "https://example.com"
