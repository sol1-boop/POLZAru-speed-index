import subprocess
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config import TELEGRAM_TOKEN, CHANNEL_ID  # Импортируем токен и идентификатор канала из config.py


# Функция для выполнения команды Lighthouse и получения метрик
def get_lighthouse_metrics(url: str, mobile: bool = False) -> str:
    try:
        # Использование абсолютного пути к lighthouse
        lighthouse_path = 'C:/Users/sol/AppData/Roaming/npm/lighthouse.cmd'

        # Общие флаги для Chrome
        chrome_flags = '--no-sandbox --disable-dev-shm-usage --headless'
        if mobile:
            chrome_flags += ' --window-size=412,823'
            lighthouse_flags = [
                lighthouse_path,
                url,
                '--output=json',
                '--quiet',
                '--emulated-form-factor=mobile',
                '--chrome-flags=' + chrome_flags
            ]
        else:
            chrome_flags += ' --window-size=1920,1080'
            lighthouse_flags = [
                lighthouse_path,
                url,
                '--output=json',
                '--quiet',
                '--preset=desktop',
                '--chrome-flags=' + chrome_flags
            ]

        result = subprocess.run(lighthouse_flags, capture_output=True, text=True)

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
        final_message = "<b>Первичные метрики:</b>\n" + json.dumps(formatted_primary_metrics, indent=2,
                                                                   ensure_ascii=False)
        final_message += "\n\n<b>Вторичные метрики:</b>\n" + json.dumps(formatted_secondary_metrics, indent=2,
                                                                        ensure_ascii=False)

        return final_message
    except subprocess.CalledProcessError as e:
        return f"Ошибка выполнения Lighthouse: {e.output}\n{e.stderr}"
    except Exception as e:
        return str(e)


# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        'Привет! Отправьте /audit_desktop <url> для аудита десктопной версии или /audit_mobile <url> для аудита мобильной версии сайта.',
        parse_mode='HTML')


# Обработчик команды /audit_desktop
async def audit_desktop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) == 0:
        await update.message.reply_text('Пожалуйста, укажите URL. Например: /audit_desktop https://example.com',
                                        parse_mode='HTML')
        return

    url = context.args[0]
    await update.message.reply_text(f'Проводится аудит десктопной версии сайта: {url}. Пожалуйста, подождите...',
                                    parse_mode='HTML')

    # Получение метрик Lighthouse для десктопной версии
    metrics = get_lighthouse_metrics(url, mobile=False)

    # Отправка метрик пользователю
    await context.bot.send_message(chat_id=CHANNEL_ID, text=f'Метрики для десктопной версии {url}:\n{metrics}',
                                   parse_mode='HTML')


# Обработчик команды /audit_mobile
async def audit_mobile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) == 0:
        await update.message.reply_text('Пожалуйста, укажите URL. Например: /audit_mobile https://example.com',
                                        parse_mode='HTML')
        return

    url = context.args[0]
    await update.message.reply_text(f'Проводится аудит мобильной версии сайта: {url}. Пожалуйста, подождите...',
                                    parse_mode='HTML')

    # Получение метрик Lighthouse для мобильной версии
    metrics = get_lighthouse_metrics(url, mobile=True)

    # Отправка метрик пользователю
    await context.bot.send_message(chat_id=CHANNEL_ID, text=f'Метрики для мобильной версии {url}:\n{metrics}',
                                   parse_mode='HTML')


def main() -> None:
    # Создание приложения с увеличением времени ожидания
    application = Application.builder().token(TELEGRAM_TOKEN).read_timeout(60).connect_timeout(60).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("audit_desktop", audit_desktop))
    application.add_handler(CommandHandler("audit_mobile", audit_mobile))

    application.run_polling()


if __name__ == '__main__':
    main()
