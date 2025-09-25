import json
from pathlib import Path
from uuid import uuid4

import pytest

from modules.config import get_telegram_settings
from modules.utils import get_storage_dir, history_file_path, load_domains


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


def test_history_file_path_sanitizes_special_characters(tmp_path, monkeypatch):
    monkeypatch.setenv("POLZA_DATA_DIR", str(tmp_path))
    domain = "https://polza.ru/catalog/?q=северная+звезда&spell=1"

    path = Path(history_file_path(domain))

    assert path.parent == tmp_path / "history_files"
    assert path.name == "history_polza.ru_catalog_q_северная_звезда_spell_1.json"
    assert all(char not in path.name for char in "?&=+")


def test_history_file_path_legacy_fallback(tmp_path, monkeypatch):
    monkeypatch.setenv("POLZA_DATA_DIR", str(tmp_path))

    legacy_dir = tmp_path / "history_files"
    legacy_dir.mkdir()
    legacy_filename = "history_example.com_path?param=1.json"
    legacy_path = legacy_dir / legacy_filename
    legacy_path.write_text("[]", encoding="utf-8")

    resolved = history_file_path("https://example.com/path?param=1")

    assert resolved == str(legacy_path)
