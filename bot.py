# bot.py

import asyncio
import logging
from datetime import datetime
import os
import subprocess
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from modules.utils import load_domains, get_telegram_settings
from modules.tracking import audit_domain, DomainTracker
from modules.metrics import summarize_history

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HISTORY_DIR = 'history_files'
if not os.path.exists(HISTORY_DIR):
    os.makedirs(HISTORY_DIR)

tracker = None  # Экземпляр DomainTracker

TELEGRAM_TOKEN, CHANNEL_ID = get_telegram_settings()


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
        await audit_domain(domain_info['domain'], context.bot, CHANNEL_ID)

    # Запуск alerts.py после каждого цикла отслеживания
    logger.info("Запуск alerts.py для проверки бюджетов...")
    try:
        subprocess.run(["python", "alerts.py"], check=True)
    except Exception as e:
        logger.exception("Не удалось запустить alerts.py: %s", e)

# Обработчик команды /start_track
async def start_track(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global tracker
    if tracker and tracker.task:
        await context.bot.send_message(chat_id=CHANNEL_ID, text="Отслеживание уже запущено.")
        return

    tracker = DomainTracker(context.bot, CHANNEL_ID)
    tracker.start()
    await context.bot.send_message(chat_id=CHANNEL_ID, text="Запущено отслеживание доменов.")


# Обработчик команды /stop_track
async def stop_track(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global tracker
    if tracker and tracker.task:
        tracker.stop()
        await context.bot.send_message(chat_id=CHANNEL_ID, text="Отслеживание остановлено.")
        tracker = None
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
                    stats = summarize_history(history_data)
                    stats_message = f"Статистика для {url}:\n"
                    for key, values in stats.items():
                        if values:
                            stats_message += f"{key}: min={values['min']:.2f}s, avg={values['avg']:.2f}s, max={values['max']:.2f}s\n"
                        else:
                            stats_message += f"{key}: нет данных\n"
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
