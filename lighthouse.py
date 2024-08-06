import subprocess
import json
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config import TELEGRAM_TOKEN, CHANNEL_ID

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

tracking_tasks = {}

async def get_lighthouse_metrics(url: str, mobile: bool = False) -> str:
    try:
        # Использование абсолютного пути к lighthouse
        lighthouse_path = '/usr/bin/lighthouse'

        # Общие флаги для Chrome
        chrome_flags = '--no-sandbox --disable-dev-shm-usage --headless'
        max_wait_for_load = '--max-wait-for-load=450000'  # Увеличение тайм-аута до 450000 мс (7.5 минут)
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

        result = await asyncio.to_thread(subprocess.run, lighthouse_flags, capture_output=True, text=True)

        # Проверка на ошибки выполнения команды
        if result.returncode != 0:
            return f"Ошибка выполнения Lighthouse: {result.stderr}"

        report = json.loads(result.stdout)

        # Извлечение необходимых метрик
        fcp = report['audits'].get('first-contentful-paint', {}).get('numericValue', 'N/A')
        fid = report['audits'].get('first-input-delay', {}).get('numericValue', 'N/A')
        tti = report['audits'].get('interactive', {}).get('numericValue', 'N/A')
        lcp = report['audits'].get('largest-contentful-paint', {}).get('numericValue', 'N/A')
        ttfb = report['audits'].get('server-response-time', {}).get('numericValue', 'N/A')
        tbt = report['audits'].get('total-blocking-time', {}).get('numericValue', 'N/A')

        # Рассчет TTIF
        if fcp != 'N/A' and fid != 'N/A':
            ttif = fcp + fid
        else:
            ttif = 'N/A'

        # Преобразование значений метрик в удобочитаемый формат
        primary_metrics = {
            'FCP (First Contentful Paint)': fcp / 1000 if isinstance(fcp, (int, float)) else fcp,
            'TTI (Time to Interactive)': tti / 1000 if isinstance(tti, (int, float)) else tti,
            'TTIF (Time to First Interaction)': ttif / 1000 if isinstance(ttif, (int, float)) else ttif,
        }

        secondary_metrics = {
            'LCP (Largest Contentful Paint)': lcp / 1000 if isinstance(lcp, (int, float)) else lcp,
            'TTFB (Time to First Byte)': ttfb if isinstance(ttfb, (int, float)) else ttfb,
            'TBT (Total Blocking Time)': tbt / 1000 if isinstance(tbt, (int, float)) else tbt,
        }

        # Удаление метрик с значением 'N/A'
        primary_metrics = {k: v for k, v in primary_metrics.items() if v != 'N/A'}
        secondary_metrics = {k: v for k, v in secondary_metrics.items() if v != 'N/A'}

        # Форматирование метрик для удобочитаемого вывода
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

        # Создание финального сообщения с метриками
        final_message = "<b>Первичные метрики:</b>\n" + json.dumps(formatted_primary_metrics, indent=2, ensure_ascii=False)
        final_message += "\n\n<b>Вторичные метрики:</b>\n" + json.dumps(formatted_secondary_metrics, indent=2, ensure_ascii=False)

        return final_message
    except subprocess.CalledProcessError as e:
        return f"Ошибка выполнения Lighthouse: {e.output}\n{e.stderr}"
    except Exception as e:
        return str(e)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Привет! Отправьте /start_track <url> для начала отслеживания мобильной версии сайта каждые 2 часа, /stop_track для остановки отслеживания, /audit_mobile <url> для проведения аудита вручную.', parse_mode='HTML')

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

    job = context.job_queue.run_repeating(track_metrics, interval=7200, first=0, data=url, name=str(chat_id))  # 7200 секунд = 2 часа
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
    await context.bot.send_message(chat_id=CHANNEL_ID, text=f'Метрики для мобильной версии {url}:\n{metrics}', parse_mode='HTML')

def main() -> None:
    application = Application.builder().token(TELEGRAM_TOKEN).read_timeout(60).connect_timeout(60).build()

    # Добавляем JobQueue в приложение
    job_queue = application.job_queue

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("start_track", start_track))
    application.add_handler(CommandHandler("stop_track", stop_track))
    application.add_handler(CommandHandler("audit_mobile", audit_mobile))

    application.run_polling()

if __name__ == '__main__':
    main()
