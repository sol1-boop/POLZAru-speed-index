import subprocess
import json
import asyncio
import logging
import requests
import time
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config import TELEGRAM_TOKEN, CHANNEL_ID
from collections import deque
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

tracking_tasks = {}
measurement_history_file = 'measurement_history.json'
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
    with open(measurement_history_file, 'w') as file:
        json.dump(list(measurement_history), file)

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
        max_wait_for_load = '--max-wait-for-load=450000'
        if mobile:
            chrome_flags += ' --window-size=412,823'
            lighthouse_flags = [
                lighthouse_path,
                url,
                '--output=json',
                '--quiet',
                '--emulated-form-factor=mobile',
                '--chrome-flags=' + chrome_flags,
                max_wait_for_load
            ]
        else:
            chrome_flags += ' --window-size=1920,1080'
            lighthouse_flags = [
                lighthouse_path,
                url,
                '--output=json',
                '--quiet',
                '--preset=desktop',
                '--chrome-flags=' + chrome_flags,
                max_wait_for_load
            ]

        backend_response_time = measure_backend_response_time(url)

        result = await asyncio.to_thread(subprocess.run, lighthouse_flags, capture_output=True, text=True)

        if result.returncode != 0:
            return {"error": f"Ошибка выполнения Lighthouse: {result.stderr}"}

        report = json.loads(result.stdout)

        fcp = report['audits'].get('first-contentful-paint', {}).get('numericValue', 'N/A')
        tti = report['audits'].get('interactive', {}).get('numericValue', 'N/A')
        lcp = report['audits'].get('largest-contentful-paint', {}).get('numericValue', 'N/A')
        ttfb = report['audits'].get('server-response-time', {}).get('numericValue', 'N/A')
        tbt = report['audits'].get('total-blocking-time', {}).get('numericValue', 'N/A')

        metrics = {
            'timestamp': datetime.now().isoformat(),
            'FCP': fcp / 1000 if isinstance(fcp, (int, float)) else fcp,
            'TTI': tti / 1000 if isinstance(tti, (int, float)) else tti,
            'Backend Response Time': backend_response_time,
            'LCP': lcp / 1000 if isinstance(lcp, (int, float)) else lcp,
            'TTFB': ttfb if isinstance(ttfb, (int, float)) else ttfb,
            'TBT': tbt / 1000 if isinstance(tbt, (int, float)) else tbt,
        }

        return metrics
    except subprocess.CalledProcessError as e:
        return {"error": f"Ошибка выполнения Lighthouse: {e.output}\n{e.stderr}"}
    except Exception as e:
        return {"error": str(e)}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Привет! Отправьте /start_track <url> для начала отслеживания мобильной версии сайта каждые 2 часа, /stop_track для остановки отслеживания, /audit_mobile <url> для проведения аудита вручную, /stats для получения статистики последних 30 дней.', parse_mode='HTML')

async def track_metrics(context: ContextTypes.DEFAULT_TYPE) -> None:
    job = context.job
    url = job.data
    metrics = await get_lighthouse_metrics(url, mobile=True)
    if 'error' in metrics:
        await context.bot.send_message(chat_id=CHANNEL_ID, text=metrics['error'], parse_mode='HTML')
    else:
        measurement_history.append(metrics)
        save_measurement_history()
        primary_metrics = {
            'FCP (First Contentful Paint)': metrics['FCP'],
            'TTI (Time to Interactive)': metrics['TTI'],
            'Backend Response Time': metrics['Backend Response Time']
        }
        secondary_metrics = {
            'LCP (Largest Contentful Paint)': metrics['LCP'],
            'TTFB (Time to First Byte)': metrics['TTFB'],
            'TBT (Total Blocking Time)': metrics['TBT']
        }

        formatted_primary_metrics = {}
        for key, value in primary_metrics.items():
            if isinstance(value, (int, float)):
                formatted_primary_metrics[key] = f'{value:.2f} s'
            else:
                formatted_primary_metrics[key] = value

        formatted_secondary_metrics = {}
        for key, value in secondary_metrics.items():
            if isinstance(value, (int, float)):
                if 'Byte' in key:
                    formatted_secondary_metrics[key] = f'{value:.0f} ms'
                else:
                    formatted_secondary_metrics[key] = f'{value:.2f} s'
            else:
                formatted_secondary_metrics[key] = value

        final_message = "<b>Первичные метрики:</b>\n" + json.dumps(formatted_primary_metrics, indent=2, ensure_ascii=False)
        final_message += "\n\n<b>Вторичные метрики:</b>\n" + json.dumps(formatted_secondary_metrics, indent=2, ensure_ascii=False)

        await context.bot.send_message(chat_id=CHANNEL_ID, text=f'Метрики для мобильной версии {url}:\n{final_message}', parse_mode='HTML')

async def start_track(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) == 0:
        await update.message.reply_text('Пожалуйста, укажите URL. Например: /start_track https://example.com', parse_mode='HTML')
        return

    url = context.args[0]
    chat_id = update.message.chat_id

    if chat_id in tracking_tasks:
        await update.message.reply_text('Отслеживание уже запущено. Для остановки введите /stop_track.', parse_mode='HTML')
        return

    job = context.job_queue.run_repeating(track_metrics, interval=7200, first=0, data=url, name=str(chat_id))
    tracking_tasks[chat_id] = job

    await update.message.reply_text(f'Запущено отслеживание мобильной версии сайта: {url}.', parse_mode='HTML')

async def stop_track(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id

    if chat_id not in tracking_tasks:
        await update.message.reply_text('Отслеживание не запущено.', parse_mode='HTML')
        return

    job = tracking_tasks.pop(chat_id)
    job.schedule_removal()

    await update.message.reply_text('Отслеживание остановлено.', parse_mode='HTML')

async def audit_mobile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) == 0:
        await update.message.reply_text('Пожалуйста, укажите URL. Например: /audit_mobile https://example.com', parse_mode='HTML')
        return

    url = context.args[0]
    await update.message.reply_text(f'Проводится аудит мобильной версии сайта: {url}. Пожалуйста, подождите...', parse_mode='HTML')

    metrics = await get_lighthouse_metrics(url, mobile=True)
    if 'error' in metrics:
        await context.bot.send_message(chat_id=CHANNEL_ID, text=metrics['error'], parse_mode='HTML')
    else:
        primary_metrics = {
            'FCP (First Contentful Paint)': metrics['FCP'],
            'TTI (Time to Interactive)': metrics['TTI'],
            'Backend Response Time': metrics['Backend Response Time']
        }
        secondary_metrics = {
            'LCP (Largest Contentful Paint)': metrics['LCP'],
            'TTFB (Time to First Byte)': metrics['TTFB'],
            'TBT (Total Blocking Time)': metrics['TBT']
        }

        formatted_primary_metrics = {}
        for key, value in primary_metrics.items():
            if isinstance(value, (int, float)):
                formatted_primary_metrics[key] = f'{value:.2f} s'
            else:
                formatted_primary_metrics[key] = value

        formatted_secondary_metrics = {}
        for key, value in secondary_metrics.items():
            if isinstance(value, (int, float)):
                if 'Byte' in key:
                    formatted_secondary_metrics[key] = f'{value:.0f} ms'
                else:
                    formatted_secondary_metrics[key] = f'{value:.2f} s'
            else:
                formatted_secondary_metrics[key] = value

        final_message = "<b>Первичные метрики:</b>\n" + json.dumps(formatted_primary_metrics, indent=2, ensure_ascii=False)
        final_message += "\n\n<b>Вторичные метрики:</b>\n" + json.dumps(formatted_secondary_metrics, indent=2, ensure_ascii=False)

        await context.bot.send_message(chat_id=CHANNEL_ID, text=f'Метрики для мобильной версии {url}:\n{final_message}', parse_mode='HTML')

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not measurement_history:
        await update.message.reply_text('Нет доступных данных для статистики.', parse_mode='HTML')
        return

    now = datetime.now()
    thirty_days_ago = now - timedelta(days=30)
    recent_measurements = [m for m in measurement_history if datetime.fromisoformat(m['timestamp']) > thirty_days_ago]

    if not recent_measurements:
        await update.message.reply_text('Нет данных за последние 30 дней.', parse_mode='HTML')
        return

    average_metrics = {
        'FCP': sum(m['FCP'] for m in recent_measurements) / len(recent_measurements),
        'TTI': sum(m['TTI'] for m in recent_measurements) / len(recent_measurements),
        'Backend Response Time': sum(m['Backend Response Time'] for m in recent_measurements) / len(recent_measurements),
        'LCP': sum(m['LCP'] for m in recent_measurements) / len(recent_measurements),
        'TTFB': sum(m['TTFB'] for m in recent_measurements) / len(recent_measurements),
        'TBT': sum(m['TBT'] for m in recent_measurements) / len(recent_measurements),
    }

    formatted_average_metrics = {}
    for key, value in average_metrics.items():
        if isinstance(value, (int, float)):
            formatted_average_metrics[key] = f'{value:.2f} s'
        else:
            formatted_average_metrics[key] = value

    final_message = "<b>Средние метрики за последние 30 дней:</b>\n" + json.dumps(formatted_average_metrics, indent=2, ensure_ascii=False)

    await update.message.reply_text(final_message, parse_mode='HTML')

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
