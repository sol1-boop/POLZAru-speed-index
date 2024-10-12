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
import os
import matplotlib.pyplot as plt
import tempfile  # Новый импорт

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

tracking_tasks = {}
domain_file = 'domain.json'

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
        }
        summary_text = f"Результаты аудита для {url}:\n"
        for key, value in summary.items():
            summary_text += f"{key}: {value if value is not None else 'N/A'}\n"

        await update.message.reply_text(summary_text)

        # Сохранение результатов в файл истории
        history_filename = f"history_{url.replace('http://', '').replace('https://', '').replace('/', '_')}.json"
        history_data = []

        if os.path.exists(history_filename):
            with open(history_filename, 'r', encoding='utf-8') as file:
                try:
                    history_data = json.load(file)
                except json.JSONDecodeError:
                    logger.error(f"Ошибка чтения JSON из файла {history_filename}. Создание нового файла.")
                    history_data = []
        else:
            # Создаем файл, если он не существует
            with open(history_filename, 'w', encoding='utf-8') as file:
                json.dump([], file, ensure_ascii=False, indent=2)

        history_data.append({
            'url': url,
            'timestamp': datetime.now().isoformat(),
            'metrics': {
                'FCP': summary['FCP'],
                'LCP': summary['LCP'],
                'TTFB': summary['TTFB'],
                'TBT': summary['TBT'],
            }
        })

        with open(history_filename, 'w', encoding='utf-8') as file:
            json.dump(history_data, file, ensure_ascii=False, indent=2)

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
    history_filename = f"history_{url.replace('http://', '').replace('https://', '').replace('/', '_')}.json"
    history_data = []

    if os.path.exists(history_filename):
        with open(history_filename, 'r', encoding='utf-8') as file:
            try:
                history_data = json.load(file)
            except json.JSONDecodeError:
                logger.error(f"Ошибка чтения JSON из файла {history_filename}. Создание нового файла.")
                history_data = []
    else:
        # Создаем файл, если он не существует
        with open(history_filename, 'w', encoding='utf-8') as file:
            json.dump([], file, ensure_ascii=False, indent=2)

    metrics_to_save = {
        'FCP': metrics.get("audits", {}).get("first-contentful-paint", {}).get("displayValue"),
        'LCP': metrics.get("audits", {}).get("largest-contentful-paint", {}).get("displayValue"),
        'TTFB': metrics.get("audits", {}).get("server-response-time", {}).get("displayValue"),
        'TBT': metrics.get("audits", {}).get("total-blocking-time", {}).get("displayValue"),
    }

    history_data.append({
        'url': url,
        'timestamp': datetime.now().isoformat(),
        'metrics': metrics_to_save
    })

    with open(history_filename, 'w', encoding='utf-8') as file:
        json.dump(history_data, file, ensure_ascii=False, indent=2)

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
    domains = load_domains()
    if not domains:
        await update.message.reply_text("Список доменов пуст или файл не найден.")
        return

    stats_message = "История замеров (последние 5 записей):\n"
    for url in domains:
        history_filename = f"history_{url.replace('http://', '').replace('https://', '').replace('/', '_')}.json"
        if os.path.exists(history_filename):
            with open(history_filename, 'r', encoding='utf-8') as file:
                try:
                    history_data = json.load(file)
                    for entry in history_data[-5:]:
                        stats_message += f"{entry['timestamp']} - {entry['url']}: {json.dumps(entry['metrics'], indent=2, ensure_ascii=False)}\n\n"
                except json.JSONDecodeError:
                    logger.error(f"Ошибка чтения JSON из файла {history_filename}. Пропуск файла.")

    await update.message.reply_text(stats_message)

def main() -> None:
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