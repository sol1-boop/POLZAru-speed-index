# modules/metrics.py

import logging
import os
import re

from modules.utils import history_file_path, load_json

logger = logging.getLogger(__name__)


def parse_metric(value, unit="s"):
    """Return numeric value of Lighthouse metric *value* in given *unit*."""
    if value:
        try:
            # Удаляем неразрывные пробелы и дополнительные пробелы
            value = value.replace("\u00A0", " ").strip()
            # Удаляем дополнительный текст из TTFB
            if "Root document took" in value:
                value = value.replace("Root document took", "").strip()
            # Извлекаем числовое значение с помощью регулярного выражения
            match = re.search(r"([\d,\.]+)", value)
            if match:
                number_str = match.group(1)
                # Удаляем разделители тысяч (запятые)
                number_str = number_str.replace(",", "")
                # Преобразуем строку в число
                number = float(number_str)
                # Приводим к нужной единице измерения
                if unit == "ms":
                    if "ms" in value.lower() or "миллисек" in value.lower():
                        return number
                    if "s" in value.lower() or "сек" in value.lower():
                        return number * 1000
                    return number
                if unit == "s":
                    if "ms" in value.lower() or "миллисек" in value.lower():
                        return number / 1000
                    if "s" in value.lower() or "сек" in value.lower():
                        return number
                    return number
                return number
            logger.error("Не удалось извлечь числовое значение из метрики: %s", value)
        except ValueError as e:
            logger.error("Ошибка при преобразовании метрики '%s': %s", value, e)
    else:
        logger.error("Пустое значение метрики: %s", value)
    return None


def load_history(domain):
    history_filepath = history_file_path(domain)
    history_data = load_json(history_filepath, [])
    if history_data:
        return history_data
    if os.path.exists(history_filepath):
        logger.error("Ошибка чтения JSON из файла %s. Пропуск файла.", history_filepath)
    else:
        logger.error("Файл истории %s не найден.", history_filepath)
    return []


def summarize_history(history_data):
    """Return min/avg/max statistics for each metric in history_data."""

    fcp_values, lcp_values, ttfb_values, tbt_values = [], [], [], []
    speed_index_values = []
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
        'Speed Index': stats(speed_index_values),
    }


def calculate_stats_for_metrics(fcp_values, lcp_values, ttfb_values, tbt_values, speed_index_values=None):
    import statistics

    if speed_index_values is None:
        speed_index_values = []

    def calculate_stats(values):
        if values:
            values.sort()
            if len(values) >= 2:
                pct = statistics.quantiles(values, n=100)
                percentile_75 = round(pct[74], 2)
                percentile_95 = round(pct[94], 2)
            else:
                percentile_75 = None
                percentile_95 = None
            return {
                'min': round(min(values), 2),
                'median': round(statistics.median(values), 2),
                'percentile_75': percentile_75,
                'percentile_95': percentile_95,

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
        'Speed Index': calculate_stats([v for v in (speed_index_values or []) if v is not None])

    }


def compute_domain_stats(history_data):
    """Extract metrics lists and statistics from *history_data*."""

    dates = [entry.get("timestamp") for entry in history_data]
    fcp_values = [parse_metric(entry.get("metrics", {}).get("FCP")) for entry in history_data]
    lcp_values = [parse_metric(entry.get("metrics", {}).get("LCP")) for entry in history_data]
    ttfb_values = [
        parse_metric(entry.get("metrics", {}).get("TTFB"), unit="s")
        for entry in history_data
    ]
    tbt_values = [
        parse_metric(entry.get("metrics", {}).get("TBT"), unit="s")
        for entry in history_data
    ]
    speed_index_values = [
        parse_metric(entry.get("metrics", {}).get("Speed Index"))
        for entry in history_data
    ]

    stats = calculate_stats_for_metrics(
        fcp_values[:],
        lcp_values[:],
        ttfb_values[:],
        tbt_values[:],
        speed_index_values[:],
    )

    metrics = {
        "FCP": fcp_values,
        "LCP": lcp_values,
        "TTFB": ttfb_values,
        "TBT": tbt_values,
        "Speed Index": speed_index_values,
    }

    return {"dates": dates, "metrics": metrics, "stats": stats}
