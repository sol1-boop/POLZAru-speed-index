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


def summarize_history(history_data):
    """Return min/avg/max statistics for each metric in history_data."""

    fcp_values, lcp_values, ttfb_values, tbt_values = [], [], [], []
    for entry in history_data:
        metrics = entry.get('metrics', {})
        fcp = parse_metric(metrics.get('FCP'))
        if fcp is not None:
            fcp_values.append(fcp)

        lcp = parse_metric(metrics.get('LCP'))
        if lcp is not None:
            lcp_values.append(lcp)

        ttfb = parse_metric(metrics.get('TTFB'), unit='ms')
        if ttfb is not None:
            ttfb_values.append(ttfb / 1000)

        tbt = parse_metric(metrics.get('TBT'), unit='ms')
        if tbt is not None:
            tbt_values.append(tbt / 1000)

    def stats(values):
        if values:
            return {
                'min': min(values),
                'avg': sum(values) / len(values),
                'max': max(values)
            }
        return None

    return {
        'FCP': stats(fcp_values),
        'LCP': stats(lcp_values),
        'TTFB': stats(ttfb_values),
        'TBT': stats(tbt_values),
    }

