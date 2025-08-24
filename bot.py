# bot.py

import asyncio
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from modules.utils import load_domains, get_telegram_settings, load_config
from modules.tracking import audit_domain, DomainTracker
from modules.metrics import compute_domain_stats, load_history
from alerts import check_and_alert

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

    cfg_headless = load_config().get('headless', True)
    headless = cfg_headless
    for arg in context.args:
        if arg.startswith('headless='):
            try:
                headless = bool(int(arg.split('=')[1]))
            except (ValueError, IndexError):
                headless = cfg_headless

    for domain_info in domains_data:
        await audit_domain(domain_info['domain'], context.bot, CHANNEL_ID, headless=headless)

    # Проверка бюджетов после аудита
    logger.info("Запуск проверки бюджетов...")
    try:
        await asyncio.to_thread(check_and_alert)
    except Exception as e:
        logger.exception("Не удалось выполнить check_and_alert: %s", e)

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
        history_data = load_history(url)
        if history_data:
            result = compute_domain_stats(history_data)
            stats_message = f"Статистика для {url}:\n"
            for key, values in result['stats'].items():
                if values['min'] is not None:
                    stats_message += (
                        f"{key}: min={values['min']:.2f}s, median={values['median']:.2f}s, max={values['max']:.2f}s\n"
                    )
                else:
                    stats_message += f"{key}: нет данных\n"
            await context.bot.send_message(chat_id=CHANNEL_ID, text=stats_message)
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
