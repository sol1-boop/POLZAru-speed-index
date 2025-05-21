from flask import Blueprint, render_template, request, redirect, url_for

from modules.utils import load_domains, save_domains, load_config, save_config
from modules.auth import login_required, login_user, logout_user


auth_bp = Blueprint('auth_bp', __name__)


@auth_bp.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    next_url = request.form.get('next') or url_for('index')
    if login_user(username, password):
        return redirect(next_url)
    else:
        error = 'Неправильный логин или пароль'
        return render_template('index.html', error=error, domains=load_domains())


@auth_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@auth_bp.route('/settings', methods=['GET', 'POST'])
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
                        'TBT': float(request.form.get('budget_tbt', 0)),
                        'Speed Index': float(request.form.get('budget_speed_index', 0)),
                        'INP': float(request.form.get('budget_inp', 0)),
                    }
                    break
            save_domains(domains)
        elif action == 'change_display_points':
            max_display_points = int(request.form.get('max_display_points', 10))
            config['max_display_points'] = max_display_points
            save_config(config)
        elif action == 'update_telegram_settings':
            telegram_token = request.form.get('telegram_token', '')
            channel_id = request.form.get('channel_id', '')
            config['telegram_token'] = telegram_token
            config['channel_id'] = channel_id
            save_config(config)

        return redirect(url_for('auth_bp.settings'))

    return render_template(
        'settings.html',
        domains=domains,
        frequency=frequency,
        max_display_points=max_display_points,
        telegram_token=telegram_token,
        channel_id=channel_id,
    )

