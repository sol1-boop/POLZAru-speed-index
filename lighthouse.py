import asyncio
import logging
import subprocess
import json
import requests
import time
from datetime import datetime, timedelta
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, ContextTypes
from config import TELEGRAM_TOKEN
import os
import shutil
import re

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
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, sync_get_lighthouse_metrics, url, mobile)

def sync_get_lighthouse_metrics(url: str, mobile: bool = False) -> dict:
    try:
        if os.name == 'nt':
            default_lighthouse_path = 'lighthouse.cmd'
        else:
            default_lighthouse_path = 'lighthouse'

        lighthouse_path = os.getenv('LIGHTHOUSE_PATH', default_lighthouse_path)

        if not shutil.which(lighthouse_path):
            logger.error(f"Lighthouse не найден по пути: {lighthouse_path}")
            return {}

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
                f'--chrome-flags={chrome_flags}',
                max_wait_for_load
            ]
        else:
            lighthouse_flags = [
                lighthouse_path,
                url,
                '--output=json',
                '--quiet',
                f'--chrome-flags={chrome_flags}',
                max_wait_for_load
            ]

        result = subprocess.run(lighthouse_flags, capture_output=True, text=True, encoding='utf-8')
        if result.returncode != 0:
            logger.error(f"Lighthouse вернул код ошибки {result.returncode} для {url}")
            logger.error(f"Сообщение об ошибке: {result.stderr}")
            return {}

        if result.stdout:
            result_json = json.loads(result.stdout)
            return result_json
        else:
            logger.error(f"Нет вывода от Lighthouse для {url}")
            return {}
    except json.JSONDecodeError as json_err:
        logger.error(f"Ошибка декодирования JSON для {url}: {json_err}")
        return {}
    except Exception as e:
        logger.exception(f"Ошибка при запуске Lighthouse для {url}: {e}")
        return {}

def parse_metric(value, unit='s'):
    if value:
        try:
            value = value.replace('\u00A0', ' ')
            cleaned_value = ''.join(c for c in value if c.isdigit() or c in ['.', ',', ' '])
            cleaned_value = cleaned_value.replace(' ', '')
            cleaned_value = cleaned_value.replace(',', '.')
            number = float(cleaned_value)
            if unit == 'ms':
                if 'ms' in value or 'миллисек' in value.lower():
                    return number
                elif 's' in value or 'сек' in value.lower():
                    return number * 1000
            elif unit == 's':
                if 's' in value or 'сек' in value.lower():
                    return number
                elif 'ms' in value or 'миллисек' in value.lower():
                    return number / 1000
            else:
                return number
        except ValueError:
            logger.error(f"Невозможно преобразовать метрику: {value}")
    else:
        logger.error(f"Пустое значение метрики: {value}")
    return None

# Функция обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Добро пожаловать! Используйте команду /start_track для начала отслеживания доменов, "
        "/audit_mobile для разового аудита или /stats для получения статистики."
    )

# Функция обработчик команды /audit_mobile
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
            try:
                with open(history_filename, 'r', encoding='utf-8') as file:
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

# Функция обработчик команды /start_track
async def start_track(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    domains = load_domains()
    if not domains:
        await update.message.reply_text("Список доменов пуст или файл не найден.")
        return

    for url in domains:
        if url in tracking_tasks:
            await update.message.reply_text(f"{url} уже отслеживается.")
            continue

        tracking_tasks[url] = context.job_queue.run_repeating(
            track_metrics,
            interval=timedelta(minutes=30),
            first=0,
            name=url,
            data=url
        )
        await update.message.reply_text(f"Запущено отслеживание для: {url}")

# Функция для периодического сбора метрик
async def track_metrics(context: ContextTypes.DEFAULT_TYPE) -> None:
    url = context.job.data
    metrics = await get_lighthouse_metrics(url, mobile=True)
    if not metrics:
        logger.error(f"Не удалось получить метрики для {url}")
        return

    history_filename = f"history_{url.replace('http://', '').replace('https://', '').replace('/', '_')}.json"
    history_data = []

    if os.path.exists(history_filename):
        try:
            with open(history_filename, 'r', encoding='utf-8') as file:
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

# Функция обработчик команды /stop_track
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

# Обновлённая функция обработчик команды /stats
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    domains = load_domains()
    if not domains:
        await update.message.reply_text("Список доменов пуст или файл не найден.")
        return

    for url in domains:
        history_filename = f"history_{url.replace('http://', '').replace('https://', '').replace('/', '_')}.json"
        domain_stats = {
            'url': url,
            'stats': {},
            'history': []
        }

        if os.path.exists(history_filename):
            try:
                with open(history_filename, 'r', encoding='utf-8') as file:
                    history_data = json.load(file)

                if history_data:
                    # Получение значений метрик для анализа
                    fcp_values = []
                    lcp_values = []
                    ttfb_values = []
                    tbt_values = []
                    measurements_list = []

                    for entry in history_data:
                        metrics = entry['metrics']
                        timestamp = entry['timestamp']
                        # Форматируем строку для записи в файл
                        metrics_str = ', '.join(f"{k}: {v}" for k, v in metrics.items())
                        measurement_str = f"Timestamp: {timestamp}, Metrics: {metrics_str}\n"

                        # Сохраняем измерения для файла
                        measurements_list.append(measurement_str)

                        fcp = parse_metric(metrics.get('FCP'))
                        if fcp is not None:
                            fcp_values.append(fcp)

                        lcp = parse_metric(metrics.get('LCP'))
                        if lcp is not None:
                            lcp_values.append(lcp)

                        ttfb = parse_metric(metrics.get('TTFB'), unit='ms')
                        if ttfb is not None:
                            ttfb_values.append(ttfb / 1000)  # Преобразуем в секунды

                        tbt = parse_metric(metrics.get('TBT'), unit='ms')
                        if tbt is not None:
                            tbt_values.append(tbt / 1000)  # Преобразуем в секунды

                    # Вычисление минимального, среднего и максимального значений
                    domain_stats['stats'] = {
                        'FCP': {
                            'min': min(fcp_values) if fcp_values else None,
                            'avg': sum(fcp_values) / len(fcp_values) if fcp_values else None,
                            'max': max(fcp_values) if fcp_values else None
                        },
                        'LCP': {
                            'min': min(lcp_values) if lcp_values else None,
                            'avg': sum(lcp_values) / len(lcp_values) if lcp_values else None,
                            'max': max(lcp_values) if lcp_values else None
                        },
                        'TTFB': {
                            'min': min(ttfb_values) if ttfb_values else None,
                            'avg': sum(ttfb_values) / len(ttfb_values) if ttfb_values else None,
                            'max': max(ttfb_values) if ttfb_values else None
                        },
                        'TBT': {
                            'min': min(tbt_values) if tbt_values else None,
                            'avg': sum(tbt_values) / len(tbt_values) if tbt_values else None,
                            'max': max(tbt_values) if tbt_values else None
                        }
                    }

                    # Формирование сообщения с метриками
                    stats_message = f"Статистика для {url}:\n"
                    for metric_name in ['FCP', 'LCP', 'TTFB', 'TBT']:
                        metric_values = domain_stats['stats'][metric_name]
                        if metric_values['min'] is not None:
                            stats_message += (
                                f"{metric_name}: "
                                f"min={metric_values['min']:.2f}s, "
                                f"avg={metric_values['avg']:.2f}s, "
                                f"max={metric_values['max']:.2f}s\n"
                            )
                        else:
                            stats_message += f"{metric_name}: нет данных\n"

                    await update.message.reply_text(stats_message)

                    # Сохраняем измерения в отдельный .txt файл для домена
                    measurements_filename = f"measurements_{url.replace('http://', '').replace('https://', '').replace('/', '_')}.txt"
                    with open(measurements_filename, 'w', encoding='utf-8') as file:
                        for measurement in measurements_list:
                            file.write(measurement)

                    # Отправляем файл с измерениями
                    await update.message.reply_document(InputFile(measurements_filename))
                    os.remove(measurements_filename)  # Удаляем файл после отправки

                else:
                    await update.message.reply_text(f"История для {url} пуста.")
            except json.JSONDecodeError:
                logger.error(f"Ошибка чтения JSON из файла {history_filename}. Пропуск файла.")
                continue
        else:
            await update.message.reply_text(f"История для {url} не найдена.")

def main() -> None:
    application = Application.builder().token(TELEGRAM_TOKEN).read_timeout(60).connect_timeout(60).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("start_track", start_track))
    application.add_handler(CommandHandler("stop_track", stop_track))
    application.add_handler(CommandHandler("audit_mobile", audit_mobile))
    application.add_handler(CommandHandler("stats", stats))

    application.run_polling()

if __name__ == '__main__':
    main()
