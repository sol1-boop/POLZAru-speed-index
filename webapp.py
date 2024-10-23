from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import json
import os
from functools import wraps
from config import ADMIN_USERNAME, ADMIN_PASSWORD

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Замените на ваш секретный ключ

DOMAIN_FILE = 'domain.json'
CONFIG_FILE = 'config.json'

# Функции для загрузки и сохранения доменов
def load_domains():
    if os.path.exists(DOMAIN_FILE):
        try:
            with open(DOMAIN_FILE, 'r', encoding='utf-8') as file:
                return json.load(file)
        except json.JSONDecodeError:
            print("Ошибка: 'domain.json' пуст или содержит некорректный JSON.")
            return []
    return []

def save_domains(domains):
    with open(DOMAIN_FILE, 'w', encoding='utf-8') as file:
        json.dump(domains, file, indent=2, ensure_ascii=False)

# Функции для загрузки и сохранения настроек
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as file:
                return json.load(file)
        except json.JSONDecodeError:
            print("Ошибка: 'config.json' пуст или содержит некорректный JSON. Используются настройки по умолчанию.")
            return {'frequency': 2}  # Значение по умолчанию
    else:
        return {'frequency': 2}  # Значение по умолчанию

def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as file:
        json.dump(config, file, indent=2, ensure_ascii=False)

# Функции для авторизации
def is_logged_in():
    return session.get('logged_in')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_logged_in():
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Функция для парсинга метрик
def parse_metric(value, unit='s'):
    if value:
        try:
            value = value.replace('\u00A0', ' ')
            cleaned_value = ''.join(c for c in value if c.isdigit() or c in ['.', ',', ' '])
            cleaned_value = cleaned_value.replace(' ', '')
            cleaned_value = cleaned_value.replace(',', '.')
            number = float(cleaned_value)
            if unit == 'ms':
                if 'ms' in value or 'миллисек' in value.lower():
                    return number
                elif 's' in value or 'сек' in value.lower():
                    return number * 1000
            elif unit == 's':
                if 's' in value or 'сек' in value.lower():
                    return number
                elif 'ms' in value or 'миллисек' in value.lower():
                    return number / 1000
                else:
                    return number
        except ValueError:
            print(f"Невозможно преобразовать метрику: {value}")
    else:
        print(f"Пустое значение метрики: {value}")
    return None

# Маршруты для входа и выхода
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    next_page = request.args.get('next') or request.form.get('next')
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(next_page or url_for('settings'))
        else:
            error = 'Неверный логин или пароль. Попробуйте снова.'
    return render_template('login.html', error=error, next=next_page)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# Маршрут для главной страницы
@app.route('/')
def index():
    domains = load_domains()
    return render_template('index.html', domains=domains)

# Маршрут для получения статистики
@app.route('/get_stats', methods=['GET'])
def get_stats():
    domain = request.args.get('domain')
    if not domain:
        return jsonify({'error': 'Домен не указан'}), 400

    # Очистка домена для безопасности (убираем '..' и '\')
    domain_safe = domain.replace('..', '').replace('\\', '')

    # Формируем имя файла истории, используя ту же логику, что и в lighthouse.py
    history_filename = f"history_{domain_safe.replace('http://', '').replace('https://', '').replace('/', '_')}.json"

    if not os.path.exists(history_filename):
        return jsonify({'error': 'Файл истории не найден'}), 404

    try:
        with open(history_filename, 'r', encoding='utf-8') as file:
            history_data = json.load(file)
    except json.JSONDecodeError:
        return jsonify({'error': 'Некорректный JSON в файле истории'}), 500

    # Сбор метрик
    fcp_values = []
    lcp_values = []
    ttfb_values = []
    tbt_values = []

    for entry in history_data:
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

    # Вычисление статистики
    def calculate_stats(values):
        if values:
            return {
                'min': min(values),
                'avg': sum(values) / len(values),
                'max': max(values)
            }
        else:
            return None

    stats = {
        'FCP': calculate_stats(fcp_values),
        'LCP': calculate_stats(lcp_values),
        'TTFB': calculate_stats(ttfb_values),
        'TBT': calculate_stats(tbt_values)
    }

    return jsonify(stats)

# Маршрут для настроек
@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    domains = load_domains()
    config = load_config()
    frequency = config.get('frequency', 2)
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            domain = request.form.get('domain')
            if domain and domain not in domains:
                domains.append(domain)
                save_domains(domains)
        elif action == 'remove':
            domain = request.form.get('domain')
            if domain in domains:
                domains.remove(domain)
                save_domains(domains)
        elif action == 'change_frequency':
            frequency = request.form.get('frequency', type=int)
            if frequency and frequency >= 1:
                config['frequency'] = frequency
                save_config(config)
        return redirect(url_for('settings'))
    return render_template('settings.html', domains=domains, frequency=frequency)

if __name__ == '__main__':
    app.run(debug=True)
