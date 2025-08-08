import requests
from modules.utils import get_telegram_settings
from modules.budget import load_budget, get_latest_metrics

TELEGRAM_TOKEN, CHANNEL_ID = get_telegram_settings()

# Функция для отправки сообщения в Телеграм
def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHANNEL_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()  # Проверка на успешность запроса
        print("Сообщение отправлено в Телеграм.")
    except requests.exceptions.RequestException as e:
        print(f"Ошибка отправки в Телеграм: {e}")


# Основная функция для проверки метрик и отправки алертов
def check_and_alert():
    budget_data = load_budget()  # Получаем бюджет из domain.json
    print("Загружен бюджет:", budget_data)  # Добавлено для отладки

    for domain_data in budget_data:
        domain = domain_data['domain']
        budget_metrics = domain_data.get('budget', {})
        print(f"\nПроверка домена: {domain}")  # Добавлено для отладки

        # Получаем последние метрики из соответствующего файла в history_files
        latest_metrics = get_latest_metrics(domain)
        print("Последние метрики:", latest_metrics)  # Добавлено для отладки

        if not latest_metrics:
            print(f"Метрики для {domain} не найдены, пропуск.")
            continue

        # Подготовка сообщения алерта
        alert_message = f"⚠️ <b>Алерт для {domain}</b> ⚠️\n\n"
        alert_triggered = False

        # Проверка каждой метрики на превышение бюджета
        for metric, threshold in budget_metrics.items():
            if metric in latest_metrics and latest_metrics[metric] > threshold:
                alert_message += f"{metric}: {latest_metrics[metric]} (бюджет: {threshold})\n"
                alert_triggered = True

        # Отправляем уведомление, если хотя бы одна метрика превышает порог
        if alert_triggered:
            print("Отправка уведомления:\n", alert_message)  # Для отладки перед отправкой
            send_telegram_alert(alert_message)
        else:
            print(f"Для {domain} превышений бюджета не обнаружено.")


# Запуск основной функции
if __name__ == "__main__":
    check_and_alert()
