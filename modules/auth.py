# modules/auth.py

from functools import wraps
from flask import session, redirect, url_for

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def login_user(username, password):
    # Замените эту функцию на вашу собственную аутентификацию
    if username == 'admin' and password == 'password':
        session['logged_in'] = True
        return True
    else:
        return False

def logout_user():
    session.pop('logged_in', None)
