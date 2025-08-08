import logging
import requests

from modules.utils import get_telegram_settings
from modules.budget import load_budget, get_latest_metrics

logger = logging.getLogger(__name__)

TELEGRAM_TOKEN, CHANNEL_ID = get_telegram_settings()


def send_telegram_alert(message):
    """Send `message` to the configured Telegram channel."""
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
    # Получаем бюджет из domain.json через модуль budget
    budget_data = load_budget()
    print("Загружен бюджет:", budget_data)  # отладка (как в новой ветке)

    for domain_data in budget_data:
        domain = domain_data['domain']
        budget_metrics = domain_data.get('budget', {})
        logger.debug("Проверка домена: %s", domain)

        latest_metrics = get_latest_metrics(domain)
        logger.debug("Последние метрики: %s", latest_metrics)

        if not latest_metrics:
            logger.warning("Метрики для %s не найдены, пропуск.", domain)
            continue

        alert_message = f"⚠️ <b>Алерт для {domain}</b> ⚠️\n\n"
        alert_triggered = False

        for metric, threshold in budget_metrics.items():
            if metric in latest_metrics and latest_metrics[metric] > threshold:
                alert_message += f"{metric}: {latest_metrics[metric]} (бюджет: {threshold})\n"
                alert_triggered = True

        if alert_triggered:
            logger.info("Отправка уведомления: %s", alert_message)
            send_telegram_alert(alert_message)
        else:
            logger.info("Для %s превышений бюджета не обнаружено.", domain)


if __name__ == "__main__":
    check_and_alert()
