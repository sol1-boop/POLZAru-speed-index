# app.py
from flask import Flask, render_template, request, jsonify
from modules.utils import load_domains, delete_history_file
from modules.config import load_config
from modules.auth import login_required
from modules.metrics import load_history, compute_domain_stats
from blueprints.auth import auth_bp
from blueprints.alerts import alerts_bp
import logging

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.register_blueprint(alerts_bp)
app.register_blueprint(auth_bp)
app.secret_key = 'your_secret_key'  # Замените на ваш секретный ключ

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
    domains = load_domains()
    return render_template('dashboard.html', domains=domains)

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
