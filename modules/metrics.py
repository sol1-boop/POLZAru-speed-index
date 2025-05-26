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
    inp_values, speed_index_values = [], []
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

        inp = parse_metric(metrics.get('INP'), unit='ms')
        if inp is not None:
            inp_values.append(inp / 1000)

        speed_index = parse_metric(metrics.get('Speed Index'))
        if speed_index is not None:
            speed_index_values.append(speed_index)

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
        'INP': stats(inp_values),
        'Speed Index': stats(speed_index_values),
    }


def calculate_stats_for_metrics(fcp_values, lcp_values, ttfb_values, tbt_values, inp_values=None, speed_index_values=None):
    import statistics

    def calculate_stats(values):
        if values:
            values.sort()
            percentiles = {'percentile_75': None, 'percentile_95': None}
            if len(values) >= 2:
                pct = statistics.quantiles(values, n=100)
                percentiles['percentile_75'] = round(pct[74], 2)
                percentiles['percentile_95'] = round(pct[94], 2)
            return {
                'min': round(min(values), 2),
                'median': round(statistics.median(values), 2),
                'percentile_75': percentiles['percentile_75'],
                'percentile_95': percentiles['percentile_95'],
                'max': round(max(values), 2)
            }
        else:
            return {
                'min': None,
                'median': None,
                'percentile_75': None,
                'percentile_95': None,
                'max': None
            }

    return {
        'FCP': calculate_stats([v for v in fcp_values if v is not None]),
        'LCP': calculate_stats([v for v in lcp_values if v is not None]),
        'TTFB': calculate_stats([v for v in ttfb_values if v is not None]),
        'TBT': calculate_stats([v for v in tbt_values if v is not None]),
        'INP': calculate_stats([v for v in (inp_values or []) if v is not None]),
        'Speed Index': calculate_stats([v for v in (speed_index_values or []) if v is not None])
    }
