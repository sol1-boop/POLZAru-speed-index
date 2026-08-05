# config.py
import os
import bcrypt
from dotenv import load_dotenv

load_dotenv()

# Hash пароля по умолчанию 'admin' (нужно изменить в production!)
DEFAULT_ADMIN_PASSWORD_HASH = bcrypt.hashpw('admin'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

users = {
    os.getenv('ADMIN_USERNAME', 'admin'): os.getenv('ADMIN_PASSWORD_HASH', DEFAULT_ADMIN_PASSWORD_HASH)
}

def verify_password(username, password):
    """Проверяет пароль пользователя с хешем."""
    if username not in users:
        return False
    stored_hash = users[username]
    if isinstance(stored_hash, str):
        stored_hash = stored_hash.encode('utf-8')
    return bcrypt.checkpw(password.encode('utf-8'), stored_hash)

def hash_password(password):
    """Хеширует пароль с помощью bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
