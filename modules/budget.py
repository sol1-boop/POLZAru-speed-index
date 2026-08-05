import json
import os
import logging

from modules.metrics import parse_metric
from modules.utils import history_file_path, resolve_data_path

logger = logging.getLogger(__name__)

HISTORY_DIR = "history_files"
DOMAIN_CONFIG = "domain.json"


def load_budget(config_path: str = DOMAIN_CONFIG):
    """Читает файл с бюджетом метрик."""

    path = resolve_data_path(config_path)
    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        logger.warning("Ошибка: файл domain.json не найден.")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка чтения JSON из {config_path}: {e}")
        return []
    except Exception as e:
        logger.exception(f"Неожиданная ошибка при загрузке бюджета: {e}")
        return []


def get_latest_metrics(domain: str, history_dir: str = HISTORY_DIR):
    """Загружает последние метрики из файла истории для указанного домена."""
    filepath = history_file_path(domain, history_dir)
    filename = os.path.basename(filepath)

    try:
        with open(filepath, "r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, list) and data:
            latest_entry = data[-1]
            raw_metrics = latest_entry.get("metrics", {})
            cleaned_data = {}
            for metric, value in raw_metrics.items():
                if isinstance(value, str):
                    numeric_value = parse_metric(
                        value, unit="s" if metric in ["TBT", "TTFB"] else "s"
                    )
                    if numeric_value is not None:
                        cleaned_data[metric] = numeric_value
            return cleaned_data
        logger.warning(f"Ошибка: данные в {filename} не являются списком или список пуст.")
        return {}
    except FileNotFoundError:
        logger.warning(f"Ошибка: файл {filename} не найден.")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка преобразования данных в файле {filename}: {e}")
        return {}
    except Exception as e:
        logger.exception(f"Неожиданная ошибка при загрузке метрик для {domain}: {e}")
        return {}
