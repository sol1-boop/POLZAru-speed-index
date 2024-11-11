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

    # Дата один месяц назад для извлечения данных за аналогичные даты прошлого месяца
    today = datetime.now()
    one_month_ago = today - timedelta(days=30)

    # Словари для метрик текущего периода и предыдущего месяца
    current_period = []
    previous_period = {
        'FCP': [],
        'LCP': [],
        'TTFB': [],
        'TBT': []
    }

    # Словарь для быстрого доступа к данным за предыдущий месяц по датам
    previous_month_data = {}

    for entry in history_data:
        timestamp = entry.get('timestamp')
        if not timestamp:
            continue

        # Преобразование строки с датой в объект datetime
        try:
            entry_date = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%f")
        except ValueError:
            continue  # Пропускаем запись, если формат даты не подходит

        metrics = entry.get('metrics', {})

        # Данные за текущий месяц
        if entry_date.month == today.month and entry_date.year == today.year:
            current_period.append({
                'timestamp': entry_date,
                'FCP': parse_metric(metrics.get('FCP')),
                'LCP': parse_metric(metrics.get('LCP')),
                'TTFB': parse_metric(metrics.get('TTFB'), unit='ms') / 1000 if metrics.get('TTFB') else None,
                'TBT': parse_metric(metrics.get('TBT'), unit='ms') / 1000 if metrics.get('TBT') else None
            })

        # Сохраняем данные предыдущего месяца в словаре по точным датам
        elif entry_date.month == one_month_ago.month and entry_date.year == one_month_ago.year:
            previous_month_data[entry_date.day] = {
                'FCP': parse_metric(metrics.get('FCP')),
                'LCP': parse_metric(metrics.get('LCP')),
                'TTFB': parse_metric(metrics.get('TTFB'), unit='ms') / 1000 if metrics.get('TTFB') else None,
                'TBT': parse_metric(metrics.get('TBT'), unit='ms') / 1000 if metrics.get('TBT') else None
            }

    # Сортируем данные текущего периода
    current_period = sorted(current_period, key=lambda x: x['timestamp'])

    # Извлекаем даты и значения метрик для текущего периода
    dates = [record['timestamp'].strftime("%Y-%m-%dT%H:%M:%S.%f") for record in current_period]
    fcp_values = [record['FCP'] for record in current_period if record['FCP'] is not None]
    lcp_values = [record['LCP'] for record in current_period if record['LCP'] is not None]
    ttfb_values = [record['TTFB'] for record in current_period if record['TTFB'] is not None]
    tbt_values = [record['TBT'] for record in current_period if record['TBT'] is not None]

    # Формируем данные для предыдущего периода, используя даты текущего периода
    for record in current_period:
        day = record['timestamp'].day
        previous_data = previous_month_data.get(day, {})
        previous_period['FCP'].append(previous_data.get('FCP'))
        previous_period['LCP'].append(previous_data.get('LCP'))
        previous_period['TTFB'].append(previous_data.get('TTFB'))
        previous_period['TBT'].append(previous_data.get('TBT'))

    # Ограничиваем количество выводимых значений для графиков
    dates = dates[-max_display_points:]
    fcp_values = fcp_values[-max_display_points:]
    lcp_values = lcp_values[-max_display_points:]
    ttfb_values = ttfb_values[-max_display_points:]
    tbt_values = tbt_values[-max_display_points:]

    # Функция для расчета статистики
    def calculate_stats(values):
        if values:
            return {
                'min': round(min(values), 2),
                'avg': round(statistics.mean(values), 2),
                'max': round(max(values), 2)
            }
        else:
            return {'min': None, 'avg': None, 'max': None}

    # Рассчитываем статистику для текущего периода
    stats = {
        'FCP': calculate_stats(fcp_values),
        'LCP': calculate_stats(lcp_values),
        'TTFB': calculate_stats(ttfb_values),
        'TBT': calculate_stats(tbt_values)
    }

    # Формируем данные для API-ответа
    data = {
        'dates': dates,
        'metrics': {
            'FCP': fcp_values,
            'LCP': lcp_values,
            'TTFB': ttfb_values,
            'TBT': tbt_values
        },
        'previous_metrics': {
            'FCP': previous_period['FCP'][:max_display_points],
            'LCP': previous_period['LCP'][:max_display_points],
            'TTFB': previous_period['TTFB'][:max_display_points],
            'TBT': previous_period['TBT'][:max_display_points]
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

@app.route('/dashboard')
def dashboard():
    domains = load_domains()
    return render_template('dashboard.html', domains=domains)

if __name__ == '__main__':
    app.run(debug=True)
