from flask import Flask, jsonify
import json
import os
import re
from datetime import datetime

app = Flask(__name__)

HISTORY_DIR = 'history_files'
DOMAIN_CONFIG = 'domain.json'


def load_budget():
    """Читает файл с бюджетом метрик."""
    try:
        with open(DOMAIN_CONFIG, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        print("Ошибка: файл domain.json не найден.")
        return []


def get_latest_metrics(domain):
    """Загружает последние метрики из файла истории для указанного домена."""
    domain_name = domain.replace('http://', '').replace('https://', '').replace('/', '')
    filename = f"history_{domain_name}.json"
    filepath = os.path.join(HISTORY_DIR, filename)

    try:
        with open(filepath, "r", encoding="utf-8") as file:
            data = json.load(file)

        # Берем последнюю запись из истории
        if isinstance(data, list) and len(data) > 0:
            latest_entry = data[-1]
            raw_metrics = latest_entry.get("metrics", {})
            cleaned_data = {}
            for metric, value in raw_metrics.items():
                if isinstance(value, str):
                    if metric == "TTFB":
                        value = value.replace("Root document took", "").strip()
                    cleaned_value = re.sub(r'[^\d.,]', '', value).replace(',', '.')
                    try:
                        numeric_value = float(cleaned_value)
                        if metric in ["TBT", "TTFB"]:
                            numeric_value /= 1000  # Переводим из мс в секунды
                        cleaned_data[metric] = numeric_value
                    except ValueError:
                        print(f"Ошибка преобразования значения метрики '{metric}': {value}")
            return cleaned_data
        else:
            print(f"Ошибка: данные в {filename} не являются списком или список пуст.")
            return {}
    except FileNotFoundError:
        print(f"Ошибка: файл {filename} не найден.")
        return {}
    except ValueError as e:
        print(f"Ошибка преобразования данных в файле {filename}: {e}")
        return {}


def check_metrics():
    """Проверяет метрики доменов на соответствие бюджету и возвращает список превышений."""
    budget_data = load_budget()
    exceeded_metrics = []

    for domain_data in budget_data:
        domain = domain_data['domain']
        budget_metrics = domain_data.get('budget', {})

        latest_metrics = get_latest_metrics(domain)
        if not latest_metrics:
            continue

        domain_exceeded = {}
        for metric, threshold in budget_metrics.items():
            if metric in latest_metrics and latest_metrics[metric] > threshold:
                domain_exceeded[metric] = {
                    "actual": latest_metrics[metric],
                    "budget": threshold
                }

        if domain_exceeded:
            exceeded_metrics.append({
                "domain": domain,
                "exceeded_metrics": domain_exceeded,
                "timestamp": datetime.now().isoformat()
            })

    return exceeded_metrics


from flask import Flask, jsonify, make_response

from flask import Flask, jsonify, make_response
import json

@app.route("/check_metrics", methods=["GET"])
def check_metrics_endpoint():
    exceeded_metrics = check_metrics()
    if exceeded_metrics:
        response_data = {
            "status": "EXCEEDED",
            "details": exceeded_metrics
        }
        response_json = json.dumps(response_data, ensure_ascii=False)  # Отключаем экранирование Unicode
        response = make_response(response_json, 404)
        response.headers["Content-Type"] = "application/json; charset=utf-8"
        return response
    else:
        response_data = {
            "status": "OK",
            "details": "Все метрики соответствуют бюджету"
        }
        response_json = json.dumps(response_data, ensure_ascii=False)  # Отключаем экранирование Unicode
        response = make_response(response_json, 200)
        response.headers["Content-Type"] = "application/json; charset=utf-8"
        return response


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
