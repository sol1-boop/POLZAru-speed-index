import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config import TELEGRAM_TOKEN, CHANNEL_ID
from lighthouse import get_lighthouse_metrics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

tracking_tasks = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Привет! Отправьте /start_track <url> для начала отслеживания мобильной версии сайта каждые 3 минуты, /stop_track для остановки отслеживания.', parse_mode='HTML')

async def track_metrics(context: ContextTypes.DEFAULT_TYPE) -> None:
    job = context.job
    url = job.data
    metrics = await get_lighthouse_metrics(url, mobile=True)
    await context.bot.send_message(chat_id=CHANNEL_ID, text=f'Метрики для мобильной версии {url}:\n{metrics}', parse_mode='HTML')

async def start_track(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) == 0:
        await update.message.reply_text('Пожалуйста, укажите URL. Например: /start_track https://example.com', parse_mode='HTML')
        return

    url = context.args[0]
    chat_id = update.message.chat_id

    if chat_id in tracking_tasks:
        await update.message.reply_text('Отслеживание уже запущено. Для остановки введите /stop_track.', parse_mode='HTML')
        return

    job = context.job_queue.run_repeating(track_metrics, interval=180, first=0, data=url, name=str(chat_id))
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

def main() -> None:
    application = Application.builder().token(TELEGRAM_TOKEN).read_timeout(60).connect_timeout(60).build()

    # Добавляем JobQueue в приложение
    job_queue = application.job_queue

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("start_track", start_track))
    application.add_handler(CommandHandler("stop_track", stop_track))

    application.run_polling()

if __name__ == '__main__':
    main()
