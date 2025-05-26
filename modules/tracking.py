import asyncio
import json
import os
import subprocess
import logging

from datetime import datetime

from modules.utils import load_domains, load_config, get_telegram_settings
from lighthouse import get_lighthouse_metrics

logger = logging.getLogger(__name__)
HISTORY_DIR = 'history_files'

async def audit_domain(url, bot, channel_id=None):
    """Run lighthouse audit for `url` and store result."""
    if channel_id is None:
        _, channel_id = get_telegram_settings()

    await bot.send_message(chat_id=channel_id, text=f"Начинаем аудит для: {url}")
    metrics = await get_lighthouse_metrics(url, mobile=True)
    if not metrics:
        await bot.send_message(chat_id=channel_id, text=f"Не удалось получить результаты аудита для {url}.")
        logger.error("Не удалось получить метрики для %s", url)
        return None

    summary = {
        "FCP": metrics.get("audits", {}).get("first-contentful-paint", {}).get("displayValue"),
        "LCP": metrics.get("audits", {}).get("largest-contentful-paint", {}).get("displayValue"),
        "TTFB": metrics.get("audits", {}).get("server-response-time", {}).get("displayValue"),
        "TBT": metrics.get("audits", {}).get("total-blocking-time", {}).get("displayValue"),
        "Speed Index": metrics.get("audits", {}).get("speed-index", {}).get("displayValue"),
        "INP": metrics.get("audits", {}).get("interaction-to-next-paint", {}).get("displayValue"),
    }
    summary_text = f"Результаты аудита для {url}:\n"
    for key, value in summary.items():
        summary_text += f"{key}: {value if value is not None else 'N/A'}\n"
    await bot.send_message(chat_id=channel_id, text=summary_text)

    history_filename = f"history_{url.replace('http://', '').replace('https://', '').replace('/', '_')}.json"
    history_filepath = os.path.join(HISTORY_DIR, history_filename)

    history_data = []
    if os.path.exists(history_filepath):
        try:
            with open(history_filepath, 'r', encoding='utf-8') as file:
                history_data = json.load(file)
        except json.JSONDecodeError:
            logger.error("Ошибка чтения JSON из файла %s. Создание нового файла.", history_filepath)

    history_data.append({'url': url, 'timestamp': datetime.now().isoformat(), 'metrics': summary})
    with open(history_filepath, 'w', encoding='utf-8') as file:
        json.dump(history_data, file, ensure_ascii=False, indent=2)

    return summary


class DomainTracker:
    def __init__(self, bot, channel_id=None):
        self.bot = bot
        if channel_id is None:
            _, channel_id = get_telegram_settings()
        self.channel_id = channel_id
        self.task = None
        self.domains = load_domains()
        self.frequency_hours = load_config().get('frequency', 2)

    async def _track_once(self):
        new_domains = load_domains()
        if new_domains:
            self.domains = new_domains
        if not self.domains:
            logger.error("Список доменов пуст. Пропуск цикла отслеживания.")
            return

        self.frequency_hours = load_config().get('frequency', self.frequency_hours)
        for domain_info in self.domains:
            await audit_domain(domain_info['domain'], self.bot, self.channel_id)

        logger.info("Запуск alerts.py для проверки бюджетов...")
        try:
            subprocess.run(["python", "alerts.py"], check=True)
        except Exception as e:
            logger.exception("Не удалось запустить alerts.py: %s", e)

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

