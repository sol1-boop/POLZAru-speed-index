# bot.py

import asyncio
import logging
from datetime import datetime
import os
import json

from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

from modules.utils import load_domains, load_config
from modules.metrics import parse_metric
from lighthouse import get_lighthouse_metrics

# Настройки для Telegram Bot
TELEGRAM_TOKEN = '6370386978:AAEEeQFUPoeFW1XgJUVNEMVvUJqlH44IQHw'  # Замените на ваш токен
CHANNEL_ID = '-1002157891114'  # Замените на ваш ID канала или чата

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HISTORY_DIR = 'history_files'
if not os.path.exists(HISTORY_DIR):
    os.makedirs(HISTORY_DIR)

tracking_task = None  # Используем одну задачу для отслеживания

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Добро пожаловать! Используйте команду /start_track для начала отслеживания доменов, "
        "/audit_mobile для разового аудита или /stats для получения статистики."
    )

# Обработчик команды /audit_mobile
async def audit_mobile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    domains_data = load_domains()
    if not domains_data:
        await context.bot.send_message(chat_id=CHANNEL_ID, text="Список доменов пуст или файл не найден.")
        return

    for domain_info in domains_data:
        url = domain_info['domain']
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
        history_filepath = os.path.join(HISTORY_DIR, history_filename)
        history_data = []

        if os.path.exists(history_filepath):
            try:
                with open(history_filepath, 'r', encoding='utf-8') as file:
                    history_data = json.load(file)
            except json.JSONDecodeError:
                logger.error(f"Ошибка чтения JSON из файла {history_filepath}. Создание нового файла.")
                history_data = []
        else:
            history_data = []

        history_data.append({
            'url': url,
            'timestamp': datetime.now().isoformat(),
            'metrics': summary
        })

        with open(history_filepath, 'w', encoding='utf-8') as file:
            json.dump(history_data, file, ensure_ascii=False, indent=2)

# Обработчик команды /start_track
async def start_track(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global tracking_task
    domains_data = load_domains()
    if not domains_data:
        await context.bot.send_message(chat_id=CHANNEL_ID, text="Список доменов пуст или файл не найден.")
        return

    if tracking_task:
        await context.bot.send_message(chat_id=CHANNEL_ID, text="Отслеживание уже запущено.")
        return

    # Инициализируем данные для отслеживания
    context.bot_data['domains_data'] = domains_data

    # Получаем частоту измерений из конфигурации
    config = load_config()
    frequency_hours = config.get('frequency', 2)
    context.bot_data['frequency_hours'] = frequency_hours

    # Запускаем задачу отслеживания
    tracking_task = context.application.create_task(track_all_domains(context))

    await context.bot.send_message(chat_id=CHANNEL_ID, text=f"Запущено отслеживание всех доменов каждые {frequency_hours} часа(ов).")

# Функция для отслеживания всех доменов
async def track_all_domains(context: ContextTypes.DEFAULT_TYPE) -> None:
    while True:
        domains_data = context.bot_data.get('domains_data', [])
        if not domains_data:
            logger.error("Список доменов пуст.")
            break

        # Получаем частоту измерений из конфигурации
        config = load_config()
        frequency_hours = config.get('frequency', 2)
        context.bot_data['frequency_hours'] = frequency_hours

        for domain_info in domains_data:
            url = domain_info['domain']
            await context.bot.send_message(chat_id=CHANNEL_ID, text=f"Начинаем аудит для: {url}")
            metrics = await get_lighthouse_metrics(url, mobile=True)
            if not metrics:
                await context.bot.send_message(chat_id=CHANNEL_ID, text=f"Не удалось получить результаты аудита для {url}.")
                logger.error(f"Не удалось получить метрики для {url}")
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

            # Отправляем сообщение в канал
            await context.bot.send_message(chat_id=CHANNEL_ID, text=summary_text)

            # Сохранение результатов в файл истории
            history_filename = f"history_{url.replace('http://', '').replace('https://', '').replace('/', '_')}.json"
            history_filepath = os.path.join(HISTORY_DIR, history_filename)
            history_data = []

            if os.path.exists(history_filepath):
                try:
                    with open(history_filepath, 'r', encoding='utf-8') as file:
                        history_data = json.load(file)
                except json.JSONDecodeError:
                    logger.error(f"Ошибка чтения JSON из файла {history_filepath}. Создание нового файла.")
                    history_data = []
            else:
                history_data = []

            history_data.append({
                'url': url,
                'timestamp': datetime.now().isoformat(),
                'metrics': summary
            })

            with open(history_filepath, 'w', encoding='utf-8') as file:
                json.dump(history_data, file, ensure_ascii=False, indent=2)

        # Ждём заданный интервал перед следующим запуском
        logger.info(f"Ждём {frequency_hours} часа(ов) до следующего запуска.")
        await asyncio.sleep(frequency_hours * 3600)

# Обработчик команды /stop_track
async def stop_track(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global tracking_task
    if tracking_task:
        tracking_task.cancel()
        tracking_task = None
        await context.bot.send_message(chat_id=CHANNEL_ID, text="Отслеживание остановлено.")
    else:
        await context.bot.send_message(chat_id=CHANNEL_ID, text="Отслеживание не запущено.")

# Обработчик команды /stats
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    domains_data = load_domains()
    if not domains_data:
        await context.bot.send_message(chat_id=CHANNEL_ID, text="Список доменов пуст или файл не найден.")
        return

    for domain_info in domains_data:
        url = domain_info['domain']
        history_filename = f"history_{url.replace('http://', '').replace('https://', '').replace('/', '_')}.json"
        history_filepath = os.path.join(HISTORY_DIR, history_filename)

        if os.path.exists(history_filepath):
            try:
                with open(history_filepath, 'r', encoding='utf-8') as file:
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
                logger.error(f"Ошибка чтения JSON из файла {history_filepath}. Пропуск файла.")
                continue
        else:
            await context.bot.send_message(chat_id=CHANNEL_ID, text=f"История для {url} не найдена.")

def main() -> None:
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).read_timeout(60).connect_timeout(60).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("start_track", start_track))
    application.add_handler(CommandHandler("stop_track", stop_track))
    application.add_handler(CommandHandler("audit_mobile", audit_mobile))
    application.add_handler(CommandHandler("stats", stats))

    # Запускаем бота
    application.run_polling()

if __name__ == '__main__':
    main()
