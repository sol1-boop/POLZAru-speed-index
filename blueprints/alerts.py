"""Blueprint providing HTTP API for budget checks."""

import json
from flask import Blueprint, make_response

from modules.alerts import check_exceedances

alerts_bp = Blueprint("alerts_bp", __name__)


@alerts_bp.route("/check_metrics", methods=["GET"])
def check_metrics_endpoint():
    exceeded = check_exceedances()
    if exceeded:
        response_data = {"status": "EXCEEDED", "details": exceeded}
        response_json = json.dumps(response_data, ensure_ascii=False)
        response = make_response(response_json, 404)
    else:
        response_data = {"status": "OK", "details": "Все метрики соответствуют бюджету"}
        response_json = json.dumps(response_data, ensure_ascii=False)
        response = make_response(response_json, 200)
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    return response
