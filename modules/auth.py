# modules/auth.py

from functools import wraps
from flask import session, redirect, url_for
from config import users  # Импортируем пользователей из config.py


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def login_user(username, password):
    # Проверяем, есть ли пользователь в словаре и совпадает ли пароль
    if username in users and users[username] == password:
        session['logged_in'] = True
        session['username'] = username  # Сохраняем имя пользователя в сессии, если потребуется
        return True
    else:
        return False

def logout_user():
    session.pop('logged_in', None)
    session.pop('username', None)
