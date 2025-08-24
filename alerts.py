import logging
import requests

from modules.alerts import check_exceedances
from modules.config import get_telegram_settings

logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = CHANNEL_ID = None


def send_telegram_alert(message):
    """Send `message` to the configured Telegram channel."""
    global TELEGRAM_TOKEN, CHANNEL_ID
    if TELEGRAM_TOKEN is None or CHANNEL_ID is None:
        TELEGRAM_TOKEN, CHANNEL_ID = get_telegram_settings()

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHANNEL_ID,
        "text": message,
        "parse_mode": "HTML",
    }
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
        logger.info("Сообщение отправлено в Телеграм.")
    except requests.exceptions.RequestException as e:
        logger.error("Ошибка отправки в Телеграм: %s", e)


def check_and_alert():
    exceeded = check_exceedances()
    if not exceeded:
        logger.info("Превышений бюджета не обнаружено.")
        return

    for item in exceeded:
        domain = item["domain"]
        alert_message = f"⚠️ <b>Алерт для {domain}</b> ⚠️\n\n"
        for metric, data in item["exceeded_metrics"].items():
            alert_message += f"{metric}: {data['actual']} (бюджет: {data['budget']})\n"
        logger.info("Отправка уведомления: %s", alert_message)
        send_telegram_alert(alert_message)


if __name__ == "__main__":
    check_and_alert()
