import json
import os
import re

HISTORY_DIR = "history_files"
DOMAIN_CONFIG = "domain.json"


def load_budget(config_path: str = DOMAIN_CONFIG):
    """Читает файл с бюджетом метрик."""
    try:
        with open(config_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        print("Ошибка: файл domain.json не найден.")
        return []


def get_latest_metrics(domain: str, history_dir: str = HISTORY_DIR):
    """Загружает последние метрики из файла истории для указанного домена."""
    domain_name = domain.replace('http://', '').replace('https://', '').replace('/', '')
    filename = f"history_{domain_name}.json"
    filepath = os.path.join(history_dir, filename)

    try:
        with open(filepath, "r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, list) and len(data) > 0:
            latest_entry = data[-1]
            raw_metrics = latest_entry.get("metrics", {})
            cleaned_data = {}
            for metric, value in raw_metrics.items():
                if isinstance(value, str):
                    if metric == "TTFB":
                        value = value.replace("Root document took", "").strip()
                    cleaned_value = re.sub(r'[^\d.,]', '', value).replace(',', '.')
                    try:
                        numeric_value = float(cleaned_value)
                        if metric in ["TBT", "TTFB"]:
                            numeric_value /= 1000
                        cleaned_data[metric] = numeric_value
                    except ValueError:
                        print(f"Ошибка преобразования значения метрики '{metric}': {value}")
            return cleaned_data
        else:
            print(f"Ошибка: данные в {filename} не являются списком или список пуст.")
            return {}
    except FileNotFoundError:
        print(f"Ошибка: файл {filename} не найден.")
        return {}
    except ValueError as e:
        print(f"Ошибка преобразования данных в файле {filename}: {e}")
        return {}
