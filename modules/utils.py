# modules/utils.py

import os
import json
import logging

logger = logging.getLogger(__name__)

def load_domains():
    domain_file = 'domain.json'
    if os.path.exists(domain_file):
        try:
            with open(domain_file, 'r', encoding='utf-8') as file:
                domains = json.load(file)
                # Убедимся, что у каждого домена есть ключ 'budget'
                for domain in domains:
                    if 'budget' not in domain:
                        domain['budget'] = {}
                return domains
        except json.JSONDecodeError:
            return []
    else:
        return []
def save_domains(domains):
    domain_file = 'domain.json'
    with open(domain_file, 'w', encoding='utf-8') as file:
        json.dump(domains, file, ensure_ascii=False, indent=2)
def load_config():
    config_file = 'config.json'
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as file:
                return json.load(file)
        except json.JSONDecodeError:
            return {}
    else:
        return {}
def save_config(config):
    config_file = 'config.json'
    with open(config_file, 'w', encoding='utf-8') as file:
        json.dump(config, file, ensure_ascii=False, indent=2)


def get_telegram_settings():
    """Return telegram token and channel id from config.json."""
    config = load_config()
    if 'telegram_token' not in config or 'channel_id' not in config:
        raise KeyError("В файле config.json отсутствуют ключи 'telegram_token' или 'channel_id'.")
    return config['telegram_token'], config['channel_id']


def get_telegram_token():
    return get_telegram_settings()[0]


def get_channel_id():
    return get_telegram_settings()[1]
def delete_history_file(domain):
    history_dir = 'history_files'
    history_filename = f"history_{domain.replace('http://', '').replace('https://', '').replace('/', '_')}.json"
    history_filepath = os.path.join(history_dir, history_filename)

    if os.path.exists(history_filepath):
        try:
            os.remove(history_filepath)
            logger.info(f"Файл истории {history_filepath} удалён.")
            return True
        except Exception as e:
            logger.error(f"Ошибка при удалении файла истории {history_filepath}: {e}")
            return False
    else:
        logger.warning(f"Файл истории {history_filepath} не найден.")
        return True  # Считаем, что файл уже удалён
