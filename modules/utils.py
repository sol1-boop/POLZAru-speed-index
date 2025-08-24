"""General utility helpers for working with JSON and history files."""

import json
import logging
import os

logger = logging.getLogger(__name__)


def load_json(filepath, default):
    """Load JSON data from *filepath* returning *default* on failure."""
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as file:
                return json.load(file)
        except json.JSONDecodeError:
            return default
    return default


def save_json(filepath, data):
    """Serialize *data* as JSON to *filepath* using UTF-8 encoding."""
    with open(filepath, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def load_domains():
    domain_file = "domain.json"
    domains = load_json(domain_file, [])
    for domain in domains:
        if "budget" not in domain:
            domain["budget"] = {}
    return domains


def save_domains(domains):
    save_json("domain.json", domains)


def history_file_path(domain, history_dir="history_files"):
    """Return path to history file for *domain* within *history_dir*."""
    filename = (
        f"history_{domain.replace('http://', '').replace('https://', '').replace('/', '_')}.json"
    )
    return os.path.join(history_dir, filename)


def delete_history_file(domain):
    history_filepath = history_file_path(domain)

    if os.path.exists(history_filepath):
        try:
            os.remove(history_filepath)
            logger.info("Файл истории %s удалён.", history_filepath)
            return True
        except Exception as e:  # pragma: no cover - log path
            logger.error("Ошибка при удалении файла истории %s: %s", history_filepath, e)
            return False
    logger.warning("Файл истории %s не найден.", history_filepath)
    return True  # Считаем, что файл уже удалён

