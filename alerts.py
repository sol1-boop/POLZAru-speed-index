import re
import json
import os
import requests
from modules.utils import get_telegram_settings

TELEGRAM_TOKEN, CHANNEL_ID = get_telegram_settings()

def get_budget():
    try:
        with open("domain.json", "r") as file:
            data = json.load(file)
        return data
    except FileNotFoundError:
        print("Ошибка: файл domain.json не найден.")
        return []


# Функция для загрузки последних метрик из файлов в history_files

def get_latest_metrics(domain):
    # Извлекаем только имя домена, убирая протокол (http, https) и слеши
    domain_name = domain.replace('http://', '').replace('https://', '').replace('/', '')
    filename = f"history_{domain_name}.json"
    filepath = os.path.join("history_files", filename)

    print(f"Пытаемся загрузить метрики из файла: {filepath}")  # Отладочное сообщение

    try:
        with open(filepath, "r", encoding="utf-8") as file:
            data = json.load(file)

        # Проверяем, что данные являются списком и содержат записи
        if isinstance(data, list) and len(data) > 0:
            # Берем последний элемент списка (последний замер)
            latest_entry = data[-1]
            raw_metrics = latest_entry.get("metrics", {})

            # Проверяем, что "metrics" действительно есть и это словарь
            if isinstance(raw_metrics, dict):
                cleaned_data = {}
                for metric, value in raw_metrics.items():
                    if isinstance(value, str):
                        # Специальная обработка для TTFB, удаление текстовой вставки
                        if metric == "TTFB":
                            value = value.replace("Root document took", "").strip()

                        # Используем регулярное выражение для извлечения числового значения
                        cleaned_value = re.sub(r'[^\d.,]', '', value)  # Оставляем только цифры, точку и запятую
                        cleaned_value = cleaned_value.replace(',', '.')  # Заменяем запятую на точку

                        try:
                            # Конвертируем значение в float
                            numeric_value = float(cleaned_value)
                            # Если метрика измеряется в миллисекундах, переводим её в секунды
                            if metric in ["TBT", "TTFB"]:
                                numeric_value /= 1000
                            cleaned_data[metric] = numeric_value
                        except ValueError:
                            print(f"Ошибка преобразования значения метрики '{metric}': {cleaned_value}")
                return cleaned_data
            else:
                print(f"Ошибка: 'metrics' не является словарем в последней записи файла {filename}.")
                return {}
        else:
            print(f"Ошибка: данные в {filename} не являются списком или список пуст.")
            return {}
    except FileNotFoundError:
        print(f"Ошибка: файл {filename} не найден.")
        return {}
    except ValueError as e:
        print(f"Ошибка преобразования данных в файле {filename}: {e}")
        return {}

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
    budget_data = get_budget()  # Получаем бюджет из domain.json
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
