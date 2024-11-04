# modules/metrics.py

import logging

logger = logging.getLogger(__name__)

def parse_metric(value, unit='s'):
    if value:
        try:
            # Удаляем неразрывные пробелы и дополнительные пробелы
            value = value.replace('\u00A0', ' ').strip()
            # Удаляем дополнительный текст из TTFB
            if 'Root document took' in value:
                value = value.replace('Root document took', '').strip()
            # Извлекаем числовое значение с помощью регулярного выражения
            import re
            match = re.search(r'([\d,\.]+)', value)
            if match:
                number_str = match.group(1)
                # Удаляем разделители тысяч (запятые)
                number_str = number_str.replace(',', '')
                # Преобразуем строку в число
                number = float(number_str)
                # Приводим к нужной единице измерения
                if unit == 'ms':
                    if 'ms' in value.lower() or 'миллисек' in value.lower():
                        return number
                    elif 's' in value.lower() or 'сек' in value.lower():
                        return number * 1000
                    else:
                        return number
                elif unit == 's':
                    if 's' in value.lower() or 'сек' in value.lower():
                        return number
                    elif 'ms' in value.lower() or 'миллисек' in value.lower():
                        return number / 1000
                    else:
                        return number
                else:
                    return number
            else:
                logger.error(f"Не удалось извлечь числовое значение из метрики: {value}")
        except ValueError as e:
            logger.error(f"Ошибка при преобразовании метрики '{value}': {e}")
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
