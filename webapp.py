# app.py
from flask import Flask, render_template, request, jsonify
from modules.utils import load_domains, delete_history_file
from modules.config import load_config
from modules.auth import login_required
from modules.metrics import load_history, compute_domain_stats, parse_metric
from blueprints.auth import auth_bp
from blueprints.alerts import alerts_bp
import logging

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.register_blueprint(alerts_bp)
app.register_blueprint(auth_bp)
app.secret_key = 'your_secret_key'  # Замените на ваш секретный ключ


def categorize_speed(value):
    """Return label for Speed Index performance category."""
    if value is None:
        return "N/A"
    if value < 4:
        return "Good"
    if value < 6:
        return "Needs Improvement"
    return "Poor"

@app.route('/')
def index():
    domains = load_domains()
    return render_template('index.html', domains=domains)


@app.route('/get_stats', methods=['GET'])
def get_stats():
    domain = request.args.get('domain')
    if not domain:
        return jsonify({'error': 'Домен не указан'}), 400

    history_data = load_history(domain)
    if not history_data:
        return jsonify({'error': 'Файл истории не найден или повреждён'}), 404

    domains = load_domains()
    budget = {}
    for d in domains:
        if d['domain'] == domain:
            budget = d.get('budget', {})
            break

    config = load_config()
    max_display_points = config.get('max_display_points', 10)

    history_data = history_data[-max_display_points:]

    result = compute_domain_stats(history_data)
    metrics = result['metrics']

    data = {
        'dates': result['dates'],
        'metrics': metrics,
        'budget': budget,
        'stats': result['stats'],
        'previous_metrics': {key: [] for key in metrics.keys()},
    }

    return jsonify(data)

@app.route('/reset_history', methods=['POST'])
@login_required  # Только авторизованные пользователи могут сбрасывать историю
def reset_history():
    data = request.get_json()
    domain = data.get('domain')
    if not domain:
        return jsonify({'error': 'Домен не указан'}), 400

    success = delete_history_file(domain)
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Не удалось удалить файл истории'}), 500

@app.route('/dashboard')
def dashboard():
    """Render summary dashboard with aggregated metrics."""
    domains = load_domains()
    domains_info = []
    total_runs = 0
    issues_found = 0
    scores = []
    distribution = {"Good": 0, "Needs Improvement": 0, "Poor": 0}
    performance_trends = {"labels": [], "scores": []}

    for domain in domains:
        history = load_history(domain["domain"])
        if history:
            total_runs += len(history)
            last_entry = history[-1]
            si = parse_metric(last_entry.get("metrics", {}).get("Speed Index"))
            lcp = parse_metric(last_entry.get("metrics", {}).get("LCP"))
            status = categorize_speed(si)
            if status in distribution:
                distribution[status] += 1
            if si is not None:
                scores.append(si)
            budget = domain.get("budget", {})
            for metric, limit in budget.items():
                unit = "ms" if metric in {"TTFB", "TBT"} else "s"
                value = parse_metric(
                    last_entry.get("metrics", {}).get(metric), unit=unit
                )
                if value is not None and value > limit:
                    issues_found += 1
                    break
            domains_info.append(
                {
                    "domain": domain["domain"],
                    "speed_score": round(si, 2) if si is not None else None,
                    "load_time": round(lcp, 2) if lcp is not None else None,
                    "last_test": last_entry.get("timestamp"),
                    "status": status,
                }
            )
            if not performance_trends["labels"]:
                performance_trends["labels"] = [
                    entry.get("timestamp") for entry in history
                ]
                performance_trends["scores"] = [
                    parse_metric(entry.get("metrics", {}).get("Speed Index"))
                    for entry in history
                ]
        else:
            domains_info.append(
                {
                    "domain": domain["domain"],
                    "speed_score": None,
                    "load_time": None,
                    "last_test": "N/A",
                    "status": "N/A",
                }
            )

    average_score = sum(scores) / len(scores) if scores else 0
    trends = performance_trends if performance_trends["labels"] else None
    return render_template(
        'dashboard.html',
        average_score=average_score,
        total_runs=total_runs,
        issues_found=issues_found,
        performance_trends=trends,
        speed_distribution=distribution,
        domains_info=domains_info,
    )

@app.route('/compare_domains', methods=['POST'])
def compare_domains():
    data = request.get_json()
    if not data or 'domains' not in data:
        return jsonify({"error": "Неверные данные"}), 400

    domains = data['domains']

    # Логика сравнения доменов
    comparison_result = {
        "domains": domains,
        "comparison": f"Сравнение для {len(domains)} доменов успешно выполнено."
    }
    return jsonify(comparison_result)

if __name__ == '__main__':
    app.run(debug=True)
