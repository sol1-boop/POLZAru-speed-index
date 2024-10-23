# lighthouse.py

import asyncio
import logging
import subprocess
import json
import requests
import time
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config import TELEGRAM_TOKEN, CHANNEL_ID
import os
import signal
import shutil

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

tracking_task = None  # Используем одну задачу для отслеживания
domain_file = 'domain.json'
CONFIG_FILE = 'config.json'

# Функции для загрузки доменов и конфигурации
def load_domains():
    if os.path.exists(domain_file):
        try:
            with open(domain_file, 'r', encoding='utf-8') as file:
                return json.load(file)
        except json.JSONDecodeError:
            logger.error("Ошибка: 'domain.json' пуст или содержит некорректный JSON.")
            return []
    return []

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as file:
                return json.load(file)
        except json.JSONDecodeError:
            logger.error("Ошибка: 'config.json' пуст или содержит некорректный JSON. Используются настройки по умолчанию.")
            return {'frequency': 2}
    else:
        return {'frequency': 2}

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
        import psutil

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
                '--only-audits=first-contentful-paint,largest-contentful-paint,server-response-time,total-blocking-time',
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
                '--only-audits=first-contentful-paint,largest-contentful-paint,server-response-time,total-blocking-time',
                f'--chrome-flags={chrome_flags}',
                max_wait_for_load
            ]

        # Запускаем Lighthouse в новой группе процессов
        if os.name != 'nt':
            process = subprocess.Popen(
                lighthouse_flags,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                preexec_fn=os.setsid
            )
        else:
            process = subprocess.Popen(
                lighthouse_flags,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )

        try:
            stdout, stderr = process.communicate(timeout=300)  # Таймаут в секундах
        except subprocess.TimeoutExpired:
            logger.error(f"Превышено время ожидания (5 минут) при аудите {url}. Прерывание процесса.")
            # Завершаем процесс и его дочерние процессы
            if os.name != 'nt':
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            else:
                process.send_signal(signal.CTRL_BREAK_EVENT)
            stdout, stderr = process.communicate()
            return {}

        if process.returncode != 0:
            logger.error(f"Lighthouse вернул код ошибки {process.returncode} для {url}")
            logger.error(f"Сообщение об ошибке: {stderr}")
            return {}

        if stdout:
            result_json = json.loads(stdout)
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
        await context.bot.send_message(chat_id=CHANNEL_ID, text="Список доменов пуст или файл не найден.")
        return

    for url in domains:
        await context.bot.send_message(chat_id=CHANNEL_ID, text=f"Начинаем аудит для: {url}")
        metrics = await get_lighthouse_metrics(url, mobile=True)
        if not metrics:
            await context.bot.send_message(chat_id=CHANNEL_ID, text=f"Не удалось получить результаты аудита для {url}.")
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

        await context.bot.send_message(chat_id=CHANNEL_ID, text=summary_text)

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
            history_data = []

        history_data.append({
            'url': url,
            'timestamp': datetime.now().isoformat(),
            'metrics': summary
        })

        with open(history_filename, 'w', encoding='utf-8') as file:
            json.dump(history_data, file, ensure_ascii=False, indent=2)

# Функция обработчик команды /start_track
async def start_track(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global tracking_task
    domains = load_domains()
    if not domains:
        await context.bot.send_message(chat_id=CHANNEL_ID, text="Список доменов пуст или файл не найден.")
        return

    if tracking_task:
        await context.bot.send_message(chat_id=CHANNEL_ID, text="Отслеживание уже запущено.")
        return

    # Инициализируем данные для отслеживания
    context.bot_data['domains'] = domains

    # Получаем частоту измерений из конфигурации
    config = load_config()
    frequency_hours = config.get('frequency', 2)
    context.bot_data['frequency_hours'] = frequency_hours

    # Запускаем задачу отслеживания
    tracking_task = context.application.create_task(track_all_domains(context))

    await context.bot.send_message(chat_id=CHANNEL_ID, text=f"Запущено отслеживание всех доменов каждые {frequency_hours} часа(ов).")

# Функция для проведения аудита всех доменов
async def track_all_domains(context: ContextTypes.DEFAULT_TYPE) -> None:
    while True:
        domains = context.bot_data.get('domains', [])
        if not domains:
            logger.error("Список доменов пуст.")
            break

        # Получаем частоту измерений из конфигурации
        config = load_config()
        frequency_hours = config.get('frequency', 2)
        context.bot_data['frequency_hours'] = frequency_hours

        for url in domains:
            await context.bot.send_message(chat_id=CHANNEL_ID, text=f"Начинаем аудит для: {url}")
            metrics = await get_lighthouse_metrics(url, mobile=True)
            if not metrics:
                await context.bot.send_message(chat_id=CHANNEL_ID, text=f"Не удалось получить результаты аудита для {url}.")
                logger.error(f"Не удалось получить метрики для {url}")
                continue

            metrics_to_save = {
                'FCP': metrics.get("audits", {}).get("first-contentful-paint", {}).get("displayValue"),
                'LCP': metrics.get("audits", {}).get("largest-contentful-paint", {}).get("displayValue"),
                'TTFB': metrics.get("audits", {}).get("server-response-time", {}).get("displayValue"),
                'TBT': metrics.get("audits", {}).get("total-blocking-time", {}).get("displayValue"),
            }

            # Формируем сообщение для отправки в канал
            summary_text = f"Результаты аудита для {url}:\n"
            for key, value in metrics_to_save.items():
                summary_text += f"{key}: {value if value is not None else 'N/A'}\n"

            # Отправляем сообщение в канал
            await context.bot.send_message(chat_id=CHANNEL_ID, text=summary_text)

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
                history_data = []

            history_data.append({
                'url': url,
                'timestamp': datetime.now().isoformat(),
                'metrics': metrics_to_save
            })

            with open(history_filename, 'w', encoding='utf-8') as file:
                json.dump(history_data, file, ensure_ascii=False, indent=2)

        # Ждём заданный интервал перед следующим запуском
        await asyncio.sleep(frequency_hours * 3600)

# Функция обработчик команды /stop_track
async def stop_track(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global tracking_task
    if tracking_task:
        tracking_task.cancel()
        tracking_task = None
        await context.bot.send_message(chat_id=CHANNEL_ID, text="Отслеживание остановлено.")
    else:
        await context.bot.send_message(chat_id=CHANNEL_ID, text="Отслеживание не запущено.")

# Функция обработчик команды /stats
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    domains = load_domains()
    if not domains:
        await context.bot.send_message(chat_id=CHANNEL_ID, text="Список доменов пуст или файл не найден.")
        return

    for url in domains:
        history_filename = f"history_{url.replace('http://', '').replace('https://', '').replace('/', '_')}.json"

        if os.path.exists(history_filename):
            try:
                with open(history_filename, 'r', encoding='utf-8') as file:
                    history_data = json.load(file)

                if history_data:
                    # Инициализируем списки для метрик
                    fcp_values = []
                    lcp_values = []
                    ttfb_values = []
                    tbt_values = []

                    for entry in history_data:
                        if 'metrics' not in entry or 'timestamp' not in entry:
                            logger.error(f"Запись не содержит 'metrics' или 'timestamp': {entry}")
                            continue

                        metrics = entry['metrics']

                        # Парсим и собираем метрики для статистики
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

                    # Формируем сообщение с метриками
                    stats_message = f"Статистика для {url}:\n"

                    if fcp_values:
                        stats_message += f"FCP: min={min(fcp_values):.2f}s, avg={sum(fcp_values) / len(fcp_values):.2f}s, max={max(fcp_values):.2f}s\n"
                    else:
                        stats_message += "FCP: нет данных\n"

                    if lcp_values:
                        stats_message += f"LCP: min={min(lcp_values):.2f}s, avg={sum(lcp_values) / len(lcp_values):.2f}s, max={max(lcp_values):.2f}s\n"
                    else:
                        stats_message += "LCP: нет данных\n"

                    if ttfb_values:
                        stats_message += f"TTFB: min={min(ttfb_values):.2f}s, avg={sum(ttfb_values) / len(ttfb_values):.2f}s, max={max(ttfb_values):.2f}s\n"
                    else:
                        stats_message += "TTFB: нет данных\n"

                    if tbt_values:
                        stats_message += f"TBT: min={min(tbt_values):.2f}s, avg={sum(tbt_values) / len(tbt_values):.2f}s, max={max(tbt_values):.2f}s\n"
                    else:
                        stats_message += "TBT: нет данных\n"

                    await context.bot.send_message(chat_id=CHANNEL_ID, text=stats_message)
                else:
                    await context.bot.send_message(chat_id=CHANNEL_ID, text=f"История для {url} пуста.")
            except json.JSONDecodeError:
                logger.error(f"Ошибка чтения JSON из файла {history_filename}. Пропуск файла.")
                continue
        else:
            await context.bot.send_message(chat_id=CHANNEL_ID, text=f"История для {url} не найдена.")

def main() -> None:
    application = Application.builder().token(TELEGRAM_TOKEN).read_timeout(60).connect_timeout(60).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("start_track", start_track))
    application.add_handler(CommandHandler("stop_track", stop_track))
    application.add_handler(CommandHandler("audit_mobile", audit_mobile))
    application.add_handler(CommandHandler("stats", stats))

    # Запускаем бота
    application.run_polling()

if __name__ == '__main__':
    main()
