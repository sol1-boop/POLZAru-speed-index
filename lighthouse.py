import subprocess
import json
import asyncio
import logging
import requests
import time
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config import TELEGRAM_TOKEN, CHANNEL_ID  # Импортируем CHANNEL_ID из config.py
from collections import deque
import os
import matplotlib.pyplot as plt
import tempfile  # Новый импорт

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

tracking_tasks = {}
measurement_history_file = 'measurement_history.json'
domain_file = 'domain.json'
measurement_history = deque(maxlen=1000)  # Увеличиваем размер deque для хранения большего количества замеров

# Загрузка истории замеров из файла
def load_measurement_history():
    if os.path.exists(measurement_history_file):
        with open(measurement_history_file, 'r') as file:
            data = json.load(file)
            for entry in data:
                measurement_history.append(entry)

# Сохранение истории замеров в файл
def save_measurement_history():
    with open(measurement_history_file, 'w', encoding='utf-8') as file:
        json.dump(list(measurement_history), file, ensure_ascii=False)

# Загрузка списка доменов из файла
def load_domains():
    if os.path.exists(domain_file):
        with open(domain_file, 'r') as file:
            return json.load(file)
    return []

def measure_backend_response_time(url: str) -> float:
    start_time = time.time()
    response = requests.get(url)
    end_time = time.time()
    response_time = end_time - start_time
    return response_time

async def get_lighthouse_metrics(url: str, mobile: bool = False) -> dict:
    try:
        lighthouse_path = 'C:/Users/sol/AppData/Roaming/npm/lighthouse.cmd'  # Убедитесь, что путь верный

        chrome_flags = '--no-sandbox --disable-dev-shm-usage --headless'
        max_wait_for_load = '--max-wait-for-load=450000'  # Изменено на 45 секунд
        if mobile:
            chrome_flags += ' --window-size=412,823'
            lighthouse_flags = [
                lighthouse_path,
                url,
                '--output=json',
                '--quiet',
                '--emulated-form-factor=mobile',
                f'--chrome-flags="{chrome_flags}"',
                max_wait_for_load
            ]
        else:
            lighthouse_flags = [
                lighthouse_path,
                url,
                '--output=json',
                '--quiet',
                f'--chrome-flags="{chrome_flags}"',
                max_wait_for_load
            ]

        result = subprocess.run(lighthouse_flags, capture_output=True, text=True, encoding='utf-8')
        if result.stdout:
            result_json = json.loads(result.stdout)
            return result_json
        else:
            logger.error(f"No output from Lighthouse for {url}")
            return {}
    except json.JSONDecodeError as json_err:
        logger.error(f"JSON decode error for {url}: {json_err}")
        return {}
    except Exception as e:
        logger.error(f"Error running Lighthouse for {url}: {e}")
        return {}

async def audit_mobile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    domains = load_domains()
    if not domains:
        await update.message.reply_text("Список доменов пуст или файл не найден.")
        return

    for url in domains:
        await update.message.reply_text(f"Начинаем аудит для: {url}")
        metrics = await get_lighthouse_metrics(url, mobile=True)
        if not metrics:
            await update.message.reply_text(f"Не удалось получить результаты аудита для {url}.")
            continue

        summary = {
            "FCP": metrics.get("audits", {}).get("first-contentful-paint", {}).get("displayValue"),
            "LCP": metrics.get("audits", {}).get("largest-contentful-paint", {}).get("displayValue"),
            "TTFB": metrics.get("audits", {}).get("server-response-time", {}).get("displayValue"),
            "TBT": metrics.get("audits", {}).get("total-blocking-time", {}).get("displayValue"),
            "Waiting for server response": metrics.get("audits", {}).get("server-response-time", {}).get("numericValue"),
        }
        summary_text = f"Результаты аудита для {url}:\n"
        for key, value in summary.items():
            summary_text += f"{key}: {value if value is not None else 'N/A'}\n"

        await update.message.reply_text(summary_text)

async def start_track(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    domains = load_domains()
    if not domains:
        await update.message.reply_text("Список доменов пуст или файл не найден.")
        return

    for url in domains:
        if url in tracking_tasks:
            await update.message.reply_text(f"{url} уже отслеживается.")
            continue

        tracking_tasks[url] = context.job_queue.run_repeating(track_metrics, interval=timedelta(minutes=30), first=0, context=url)
        await update.message.reply_text(f"Запущено отслеживание для: {url}")

async def track_metrics(context: ContextTypes.DEFAULT_TYPE) -> None:
    url = context.job.context
    metrics = await get_lighthouse_metrics(url, mobile=True)
    measurement_history.append({
        'url': url,
        'timestamp': datetime.now().isoformat(),
        'metrics': metrics
    })
    save_measurement_history()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Добро пожаловать! Используйте команду /start_track для начала отслеживания доменов или /audit_mobile для разового аудита.")

async def stop_track(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    domains = load_domains()
    if not domains:
        await update.message.reply_text("Список доменов пуст или файл не найден.")
        return

    for url in domains:
        if url in tracking_tasks:
            tracking_tasks[url].schedule_removal()
            del tracking_tasks[url]
            await update.message.reply_text(f"Отслеживание для {url} остановлено.")
        else:
            await update.message.reply_text(f"{url} не отслеживается.")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not measurement_history:
        await update.message.reply_text("История замеров пуста.")
        return

    stats_message = "История замеров (последние 5 записей):\n"
    for entry in list(measurement_history)[-5:]:
        stats_message += f"{entry['timestamp']} - {entry['url']}: {json.dumps(entry['metrics'], indent=2, ensure_ascii=False)}\n\n"

    await update.message.reply_text(stats_message)

def main() -> None:
    load_measurement_history()

    application = Application.builder().token(TELEGRAM_TOKEN).read_timeout(60).connect_timeout(60).build()

    job_queue = application.job_queue

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("start_track", start_track))
    application.add_handler(CommandHandler("stop_track", stop_track))
    application.add_handler(CommandHandler("audit_mobile", audit_mobile))
    application.add_handler(CommandHandler("stats", stats))

    application.run_polling()

if __name__ == '__main__':
    main()