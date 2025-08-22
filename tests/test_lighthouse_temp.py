import pathlib

import lighthouse
from lighthouse import create_temp_chrome_profile, cleanup_temp_chrome_data


def test_create_temp_chrome_profile(tmp_path, monkeypatch):
    monkeypatch.setattr(lighthouse.tempfile, "gettempdir", lambda: str(tmp_path))
    path = pathlib.Path(create_temp_chrome_profile())
    assert path.exists()
    assert path.parent == tmp_path
    assert path.name.startswith("chrome_profile_")
    cleanup_temp_chrome_data()
    assert not path.exists()


def test_cleanup_temp_chrome_data(tmp_path, monkeypatch):
    monkeypatch.setattr(lighthouse.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(pathlib.Path, "home", lambda: tmp_path)

    chrome_dir = tmp_path / "chrome-123"
    chrome_dir.mkdir()
    profile_dir = tmp_path / "chrome_profile_abc"
    profile_dir.mkdir()
    other_dir = tmp_path / "keep"
    other_dir.mkdir()

    cleanup_temp_chrome_data()

    assert not chrome_dir.exists()
    assert not profile_dir.exists()
    assert other_dir.exists()
