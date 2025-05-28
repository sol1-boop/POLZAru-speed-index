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
                "speed-index": {"displayValue": "1.5 s"}

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

