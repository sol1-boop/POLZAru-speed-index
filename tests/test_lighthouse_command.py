"""Tests for lighthouse command resolution."""

import importlib

import lighthouse


def reload_module(monkeypatch):
    importlib.reload(lighthouse)
    monkeypatch.setattr(lighthouse, 'load_config', lambda: {})


def test_resolve_lighthouse_from_env(monkeypatch):
    reload_module(monkeypatch)
    monkeypatch.setenv('LIGHTHOUSE_PATH', '/usr/bin/lighthouse')

    def fake_which(cmd):
        return cmd if cmd == '/usr/bin/lighthouse' else None

    monkeypatch.setattr(lighthouse.shutil, 'which', fake_which)

    command = lighthouse.resolve_lighthouse_command()
    assert command == ['/usr/bin/lighthouse']


def test_resolve_lighthouse_from_config(monkeypatch):
    reload_module(monkeypatch)
    monkeypatch.delenv('LIGHTHOUSE_PATH', raising=False)
    monkeypatch.setattr(lighthouse, 'load_config', lambda: {'lighthouse_path': '/opt/lh'})

    def fake_which(cmd):
        return cmd if cmd == '/opt/lh' else None

    monkeypatch.setattr(lighthouse.shutil, 'which', fake_which)

    command = lighthouse.resolve_lighthouse_command()
    assert command == ['/opt/lh']


def test_resolve_lighthouse_fallback_to_npx(monkeypatch):
    reload_module(monkeypatch)
    monkeypatch.delenv('LIGHTHOUSE_PATH', raising=False)

    def fake_which(cmd):
        if cmd == 'npx':
            return 'npx'
        return None

    monkeypatch.setattr(lighthouse.shutil, 'which', fake_which)
    monkeypatch.setattr(lighthouse.Path, 'exists', lambda self: False)

    command = lighthouse.resolve_lighthouse_command()
    assert command == ['npx', 'lighthouse']
