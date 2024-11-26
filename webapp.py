# app.py

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from modules.utils import load_domains, save_domains, load_config, save_config, delete_history_file
from modules.auth import login_required, login_user, logout_user
from modules.metrics import load_history, parse_metric
from alerts_api import alerts_api
from datetime import datetime, timedelta
import os
import statistics
import logging

logging.basicConfig(level=logging.DEBUG)


app = Flask(__name__)
app.register_blueprint(alerts_api)
app.secret_key = 'your_secret_key'  # Замените на ваш секретный ключ

@app.route('/')
def index():
    domains = load_domains()
    return render_template('index.html', domains=domains)

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    next_url = request.form.get('next') or url_for('index')
    if login_user(username, password):
        return redirect(next_url)
    else:
        error = 'Неправильный логин или пароль'
        return render_template('index.html', error=error, domains=load_domains())

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    domains = load_domains()
    config = load_config()
    frequency = config.get('frequency', 2)
    max_display_points = config.get('max_display_points', 10)
    telegram_token = config.get('telegram_token', '')
    channel_id = config.get('channel_id', '')

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            domain = request.form.get('domain')
            if domain:
                domains.append({'domain': domain, 'budget': {}})
                save_domains(domains)
        elif action == 'remove':
            domain_to_remove = request.form.get('domain')
            domains = [d for d in domains if d['domain'] != domain_to_remove]
            save_domains(domains)
        elif action == 'change_frequency':
            frequency = int(request.form.get('frequency', 2))
            config['frequency'] = frequency
            save_config(config)
        elif action == 'update_budget':
            domain = request.form.get('domain')
            for d in domains:
                if d['domain'] == domain:
                    d['budget'] = {
                        'FCP': float(request.form.get('budget_fcp', 0)),
                        'LCP': float(request.form.get('budget_lcp', 0)),
                        'TTFB': float(request.form.get('budget_ttfb', 0)),
                        'TBT': float(request.form.get('budget_tbt', 0))
                    }
                    break
            save_domains(domains)
        elif action == 'change_display_points':
            max_display_points = int(request.form.get('max_display_points', 10))
            config['max_display_points'] = max_display_points
            save_config(config)
        elif action == 'update_telegram_settings':
            # Сохранение настроек Telegram
            telegram_token = request.form.get('telegram_token', '')
            channel_id = request.form.get('channel_id', '')
            config['telegram_token'] = telegram_token
            config['channel_id'] = channel_id
            save_config(config)

        return redirect(url_for('settings'))

    return render_template(
        'settings.html',
        domains=domains,
        frequency=frequency,
        max_display_points=max_display_points,
        telegram_token=telegram_token,
        channel_id=channel_id
    )

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

    dates = [entry.get('timestamp') for entry in history_data]
    fcp_values = [parse_metric(entry.get('metrics', {}).get('FCP')) for entry in history_data]
    lcp_values = [parse_metric(entry.get('metrics', {}).get('LCP')) for entry in history_data]
    ttfb_values = [parse_metric(entry.get('metrics', {}).get('TTFB'), unit='ms') / 1000 if entry.get('metrics', {}).get('TTFB') else None for entry in history_data]
    tbt_values = [parse_metric(entry.get('metrics', {}).get('TBT'), unit='ms') / 1000 if entry.get('metrics', {}).get('TBT') else None for entry in history_data]

    stats = calculate_stats_for_metrics(fcp_values[:], lcp_values[:], ttfb_values[:], tbt_values[:])

    metrics = {
        'FCP': fcp_values,
        'LCP': lcp_values,
        'TTFB': ttfb_values,
        'TBT': tbt_values
    }

    # Добавление данных для предыдущих периодов (опционально)
    previous_metrics = {key: [] for key in metrics.keys()}
    if len(history_data) > max_display_points:
        for metric in metrics.keys():
            previous_metrics[metric] = metrics[metric][:max_display_points]

    data = {
        'dates': dates,
        'metrics': metrics,
        'budget': budget,
        'stats': stats,
        'previous_metrics': previous_metrics
    }

    return jsonify(data)


def calculate_stats_for_metrics(fcp_values, lcp_values, ttfb_values, tbt_values):
    def calculate_stats(values):
        if values:
            values.sort()
            return {
                'min': round(min(values), 2),
                'median': round(statistics.median(values), 2),
                'percentile_75': round(statistics.quantiles(values, n=100)[74], 2),
                'percentile_95': round(statistics.quantiles(values, n=100)[94], 2),
                'max': round(max(values), 2)
            }
        else:
            return {'min': None, 'median': None, 'percentile_75': None, 'percentile_95': None, 'max': None}

    return {
        'FCP': calculate_stats([v for v in fcp_values if v is not None]),
        'LCP': calculate_stats([v for v in lcp_values if v is not None]),
        'TTFB': calculate_stats([v for v in ttfb_values if v is not None]),
        'TBT': calculate_stats([v for v in tbt_values if v is not None])
    }

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
