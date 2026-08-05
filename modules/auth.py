# modules/auth.py

from functools import wraps
from flask import session, redirect, url_for
from config import verify_password  # Импортируем функцию проверки пароля

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def login_user(username, password):
    # Проверяем логин и пароль с использованием хеширования
    if verify_password(username, password):
        session['logged_in'] = True
        session['username'] = username  # Сохраняем имя пользователя в сессии, если потребуется
        return True
    else:
        return False

def logout_user():
    session.pop('logged_in', None)
    session.pop('username', None)
