import json
import logging
import os
import requests

from modules.utils import get_telegram_settings
from modules.metrics import parse_metric

logger = logging.getLogger(__name__)

TELEGRAM_TOKEN, CHANNEL_ID = get_telegram_settings()


def get_budget():
    """Return budget configuration from domain.json."""
    try:
        with open("domain.json", "r", encoding="utf-8") as file:
            data = json.load(file)
        return data
    except FileNotFoundError:
        logger.error("Ошибка: файл domain.json не найден.")
        return []


def get_latest_metrics(domain):
    """Return latest metrics for a domain from history files."""
    domain_name = domain.replace('http://', '').replace('https://', '').replace('/', '')
    filename = f"history_{domain_name}.json"
    filepath = os.path.join("history_files", filename)

    logger.debug("Пытаемся загрузить метрики из файла: %s", filepath)

    try:
        with open(filepath, "r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, list) and data:
            latest_entry = data[-1]
            raw_metrics = latest_entry.get("metrics", {})

            if isinstance(raw_metrics, dict):
                cleaned_data = {}
                for metric, value in raw_metrics.items():
                    parsed = parse_metric(value)
                    if parsed is not None:
                        cleaned_data[metric] = parsed
                return cleaned_data
            logger.error("'metrics' не является словарем в последней записи файла %s.", filename)
            return {}
        logger.error("Данные в %s не являются списком или список пуст.", filename)
        return {}
    except FileNotFoundError:
        logger.error("Ошибка: файл %s не найден.", filename)
        return {}
    except ValueError as e:
        logger.error("Ошибка преобразования данных в файле %s: %s", filename, e)
        return {}


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
    """Check metrics against budget and send alerts if needed."""
    budget_data = get_budget()
    logger.debug("Загружен бюджет: %s", budget_data)

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

