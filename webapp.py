# app.py

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from modules.utils import load_domains, save_domains, load_config, save_config, delete_history_file
from modules.auth import login_required, login_user, logout_user
from modules.metrics import load_history, parse_metric
from datetime import datetime
import os

app = Flask(__name__)
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

        return redirect(url_for('settings'))

    return render_template('settings.html', domains=domains, frequency=frequency, max_display_points=max_display_points)

@app.route('/get_stats', methods=['GET'])
def get_stats():
    domain = request.args.get('domain')
    if not domain:
        return jsonify({'error': 'Домен не указан'}), 400

    history_data = load_history(domain)
    if not history_data:
        return jsonify({'error': 'Файл истории не найден или повреждён'}), 404

    # Получаем бюджет для данного домена
    domains = load_domains()
    budget = {}
    for d in domains:
        if d['domain'] == domain:
            budget = d.get('budget', {})
            break

    # Загружаем настройку количества отображаемых значений
    config = load_config()
    max_display_points = config.get('max_display_points', 10)

    # Сбор метрик и дат для графика
    dates = []
    fcp_values = []
    lcp_values = []
    ttfb_values = []
    tbt_values = []

    for entry in history_data:
        timestamp = entry.get('timestamp')
        if not timestamp:
            continue
        dates.append(timestamp)

        metrics = entry.get('metrics', {})

        fcp = parse_metric(metrics.get('FCP'))
        if fcp is not None:
            fcp_values.append(fcp)

        lcp = parse_metric(metrics.get('LCP'))
        if lcp is not None:
            lcp_values.append(lcp)

        ttfb = parse_metric(metrics.get('TTFB'), unit='ms')
        if ttfb is not None:
            ttfb_values.append(ttfb / 1000)  # Переводим в секунды

        tbt = parse_metric(metrics.get('TBT'), unit='ms')
        if tbt is not None:
            tbt_values.append(tbt / 1000)  # Переводим в секунды

    # Инвертируем списки, чтобы самые новые данные были первыми
    dates = dates[::-1]
    fcp_values = fcp_values[::-1]
    lcp_values = lcp_values[::-1]
    ttfb_values = ttfb_values[::-1]
    tbt_values = tbt_values[::-1]

    # Ограничиваем количество выводимых значений
    dates = dates[:max_display_points]
    fcp_values = fcp_values[:max_display_points]
    lcp_values = lcp_values[:max_display_points]
    ttfb_values = ttfb_values[:max_display_points]
    tbt_values = tbt_values[:max_display_points]

    # Вычисление статистики (минимум, среднее, максимум) для каждой метрики
    import statistics

    def calculate_stats(values):
        if values:
            return {
                'min': round(min(values), 2),
                'avg': round(statistics.mean(values), 2),
                'max': round(max(values), 2)
            }
        else:
            return {'min': None, 'avg': None, 'max': None}

    stats = {
        'FCP': calculate_stats(fcp_values),
        'LCP': calculate_stats(lcp_values),
        'TTFB': calculate_stats(ttfb_values),
        'TBT': calculate_stats(tbt_values)
    }

    # Формирование данных для ответа
    data = {
        'dates': dates,
        'metrics': {
            'FCP': fcp_values,
            'LCP': lcp_values,
            'TTFB': ttfb_values,
            'TBT': tbt_values
        },
        'budget': budget,
        'stats': stats
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

if __name__ == '__main__':
    app.run(debug=True)
