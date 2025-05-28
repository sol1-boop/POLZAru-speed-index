import asyncio
import json
import types

import pytest

from modules import tracking


class DummyBot:
    def __init__(self):
        self.sent = []

    async def send_message(self, chat_id, text):
        self.sent.append((chat_id, text))


async def test_audit_domain(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "history_files").mkdir()

    async def fake_metrics(url, mobile=True, headless=True):
        return {
            "audits": {
                "first-contentful-paint": {"displayValue": "1 s"},
                "largest-contentful-paint": {"displayValue": "2 s"},
                "server-response-time": {"displayValue": "100 ms"},
                "total-blocking-time": {"displayValue": "50 ms"},
                "speed-index": {"displayValue": "1.5 s"},
                "interaction-to-next-paint": {"displayValue": "200 ms"},

            }
        }

    monkeypatch.setattr(tracking, "get_lighthouse_metrics", fake_metrics)
    bot = DummyBot()
    await tracking.audit_domain("example.com", bot, channel_id=1)

    assert len(bot.sent) >= 2
    history_file = tmp_path / "history_files" / "history_example.com.json"
    assert history_file.exists()
    data = json.loads(history_file.read_text())
    assert data[0]["metrics"]["FCP"] == "1 s"
    assert data[0]["metrics"]["INP"] == "200 ms"


async def test_audit_domain_experimental_inp(tmp_path, monkeypatch):
    """Ensure audit_domain works with experimental INP metrics."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "history_files").mkdir()

    async def fake_metrics(url, mobile=True, headless=True):
        return {
            "audits": {
                "first-contentful-paint": {"displayValue": "1 s"},
                "largest-contentful-paint": {"displayValue": "2 s"},
                "server-response-time": {"displayValue": "100 ms"},
                "total-blocking-time": {"displayValue": "50 ms"},
                "speed-index": {"displayValue": "1.5 s"},
                "experimental-interaction-to-next-paint": {"displayValue": "210 ms"},
            }
        }

    monkeypatch.setattr(tracking, "get_lighthouse_metrics", fake_metrics)
    bot = DummyBot()
    await tracking.audit_domain("example.com", bot, channel_id=1)

    history_file = tmp_path / "history_files" / "history_example.com.json"
    data = json.loads(history_file.read_text())
    assert data[0]["metrics"]["INP"] == "210 ms"


async def test_audit_domain_numeric_inp(tmp_path, monkeypatch):
    """Ensure INP is read from numericValue when displayValue is missing."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "history_files").mkdir()

    async def fake_metrics(url, mobile=True, headless=True):
        return {
            "audits": {
                "first-contentful-paint": {"displayValue": "1 s"},
                "largest-contentful-paint": {"displayValue": "2 s"},
                "server-response-time": {"displayValue": "100 ms"},
                "total-blocking-time": {"displayValue": "50 ms"},
                "speed-index": {"displayValue": "1.5 s"},
                "interaction-to-next-paint": {"numericValue": 230},
            }
        }

    monkeypatch.setattr(tracking, "get_lighthouse_metrics", fake_metrics)
    bot = DummyBot()
    await tracking.audit_domain("example.com", bot, channel_id=1)

    history_file = tmp_path / "history_files" / "history_example.com.json"
    data = json.loads(history_file.read_text())
    assert data[0]["metrics"]["INP"] == "230 ms"


async def test_audit_domain_inp_display_na(tmp_path, monkeypatch):
    """INP displayValue of 'N/A' falls back to numericValue."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "history_files").mkdir()

    async def fake_metrics(url, mobile=True, headless=True):
        return {
            "audits": {
                "first-contentful-paint": {"displayValue": "1 s"},
                "largest-contentful-paint": {"displayValue": "2 s"},
                "server-response-time": {"displayValue": "100 ms"},
                "total-blocking-time": {"displayValue": "50 ms"},
                "speed-index": {"displayValue": "1.5 s"},
                "interaction-to-next-paint": {
                    "displayValue": "N/A",
                    "numericValue": 250,
                },
            }
        }

    monkeypatch.setattr(tracking, "get_lighthouse_metrics", fake_metrics)
    bot = DummyBot()
    await tracking.audit_domain("example.com", bot, channel_id=1)

    history_file = tmp_path / "history_files" / "history_example.com.json"
    data = json.loads(history_file.read_text())
    assert data[0]["metrics"]["INP"] == "250 ms"


def test_domain_tracker_start_stop(monkeypatch):
    bot = DummyBot()
    tracker = tracking.DomainTracker(bot, channel_id=1)

    async def dummy_run(self):
        pass
    monkeypatch.setattr(tracking.DomainTracker, "_run", dummy_run)

    class DummyTask:
        def cancel(self):
            self.cancelled = True

    monkeypatch.setattr(asyncio, "create_task", lambda coro: DummyTask())

    tracker.start()
    assert tracker.task is not None
    tracker.stop()
    assert tracker.task is None

