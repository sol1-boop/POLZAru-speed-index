from flask import Blueprint, make_response, Flask
import json
from datetime import datetime
from modules.budget import load_budget, get_latest_metrics

alerts_api = Blueprint('alerts_api', __name__)


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

@alerts_api.route("/check_metrics", methods=["GET"])
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
    app = Flask(__name__)
    app.register_blueprint(alerts_api)
    app.run(host="0.0.0.0", port=5000)
