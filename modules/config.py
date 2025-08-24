"""Helper functions for application configuration."""

import os
from .utils import load_json, save_json

CONFIG_FILE = "config.json"


def load_config():
    """Load configuration from CONFIG_FILE."""
    return load_json(CONFIG_FILE, {})


def save_config(config):
    """Persist *config* into CONFIG_FILE."""
    save_json(CONFIG_FILE, config)


def get_telegram_settings():
    """Return telegram token and channel id from environment or config.json."""
    token = os.getenv("TELEGRAM_TOKEN")
    channel = os.getenv("CHANNEL_ID")
    if token and channel:
        return token, channel
    config = load_config()
    if "telegram_token" not in config or "channel_id" not in config:
        raise KeyError(
            "В файле config.json отсутствуют ключи 'telegram_token' или 'channel_id'."
        )
    return config["telegram_token"], config["channel_id"]


def get_telegram_token():
    """Shortcut for the telegram bot token."""
    return get_telegram_settings()[0]


def get_channel_id():
    """Shortcut for the telegram channel id."""
    return get_telegram_settings()[1]

