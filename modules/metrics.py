# modules/metrics.py

import logging

logger = logging.getLogger(__name__)

def parse_metric(value, unit='s'):
    if value:
        try:
            value = value.replace('\u00A0', ' ')
            cleaned_value = ''.join(c for c in value if c.isdigit() or c in ['.', ',', ' '])
            cleaned_value = cleaned_value.replace(' ', '')
            cleaned_value = cleaned_value.replace(',', '.')
            number = float(cleaned_value)
            if unit == 'ms':
                if 'ms' in value or 'миллисек' in value.lower():
                    return number
                elif 's' in value or 'сек' in value.lower():
                    return number * 1000
                else:
                    return number
            elif unit == 's':
                if 's' in value or 'сек' in value.lower():
                    return number
                elif 'ms' in value or 'миллисек' in value.lower():
                    return number / 1000
                else:
                    return number
            else:
                return number
        except ValueError:
            logger.error(f"Невозможно преобразовать метрику: {value}")
    else:
        logger.error(f"Пустое значение метрики: {value}")
    return None

def load_history(domain):
    import os
    import json
    history_dir = 'history_files'
    history_filename = f"history_{domain.replace('http://', '').replace('https://', '').replace('/', '_')}.json"
    history_filepath = os.path.join(history_dir, history_filename)

    if os.path.exists(history_filepath):
        try:
            with open(history_filepath, 'r', encoding='utf-8') as file:
                history_data = json.load(file)
            return history_data
        except json.JSONDecodeError:
            logger.error(f"Ошибка чтения JSON из файла {history_filepath}. Пропуск файла.")
            return []
    else:
        logger.error(f"Файл истории {history_filepath} не найден.")
        return []
