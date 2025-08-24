import asyncio
import json
import os
import logging
from datetime import datetime

from alerts import check_and_alert
from lighthouse import get_lighthouse_metrics
from modules.utils import (
    get_telegram_settings,
    history_file_path,
    load_config,
    load_domains,
    load_json,
    save_json,
)

logger = logging.getLogger(__name__)

async def audit_domain(url, bot, channel_id=None, headless=True):
    """Run lighthouse audit for `url` and store result."""
    if channel_id is None:
        _, channel_id = get_telegram_settings()

    await bot.send_message(chat_id=channel_id, text=f"Начинаем аудит для: {url}")
    metrics = await get_lighthouse_metrics(url, mobile=True, headless=headless)
    if not metrics:
        await bot.send_message(chat_id=channel_id, text=f"Не удалось получить результаты аудита для {url}.")
        logger.error("Не удалось получить метрики для %s", url)
        return None

    audits = metrics.get("audits", {})


    summary = {
        "FCP": audits.get("first-contentful-paint", {}).get("displayValue"),
        "LCP": audits.get("largest-contentful-paint", {}).get("displayValue"),
        "TTFB": audits.get("server-response-time", {}).get("displayValue"),
        "TBT": audits.get("total-blocking-time", {}).get("displayValue"),
        "Speed Index": audits.get("speed-index", {}).get("displayValue"),
    }
    summary_text = f"Результаты аудита для {url}:\n"
    for key, value in summary.items():
        summary_text += f"{key}: {value if value is not None else 'N/A'}\n"
    await bot.send_message(chat_id=channel_id, text=summary_text)

    history_filepath = history_file_path(url)
    os.makedirs(os.path.dirname(history_filepath), exist_ok=True)

    history_data = load_json(history_filepath, [])
    history_data.append({'url': url, 'timestamp': datetime.now().isoformat(), 'metrics': summary})
    save_json(history_filepath, history_data)

    return summary


class DomainTracker:
    """Periodically audit configured domains via Lighthouse."""
    def __init__(self, bot, channel_id=None):
        self.bot = bot
        if channel_id is None:
            _, channel_id = get_telegram_settings()
        self.channel_id = channel_id
        self.task = None
        self.domains = load_domains()
        cfg = load_config()
        self.frequency_hours = cfg.get('frequency', 2)
        self.headless = cfg.get('headless', True)

    async def _track_once(self):
        new_domains = load_domains()
        if new_domains:
            self.domains = new_domains
        if not self.domains:
            logger.error("Список доменов пуст. Пропуск цикла отслеживания.")
            return

        cfg = load_config()
        self.frequency_hours = cfg.get('frequency', self.frequency_hours)
        self.headless = cfg.get('headless', self.headless)
        for domain_info in self.domains:
            await audit_domain(
                domain_info['domain'],
                self.bot,
                self.channel_id,
                headless=self.headless,
            )

        logger.info("Запуск проверки бюджетов...")
        try:
            await asyncio.to_thread(check_and_alert)
        except Exception as e:
            logger.exception("Не удалось выполнить check_and_alert: %s", e)

    async def _run(self):
        try:
            while True:
                await self._track_once()
                await asyncio.sleep(self.frequency_hours * 3600)
        except asyncio.CancelledError:
            logger.info("Tracking loop cancelled.")

    def start(self):
        if not self.task:
            self.task = asyncio.create_task(self._run())
        return self.task

    def stop(self):
        if self.task:
            self.task.cancel()
            self.task = None

