"""General utility helpers for working with JSON and history files."""

import json
import logging
import os
from pathlib import Path
from typing import Union

logger = logging.getLogger(__name__)


def _has_storage_hint(directory: Path) -> bool:
    """Return ``True`` if *directory* looks like a storage location."""

    return any(
        (directory / name).exists()
        for name in ("domain.json", "history_files", "config.json")
    )


def get_storage_dir() -> Path:
    """Return the base directory that stores mutable data files."""

    env_dir = os.getenv("POLZA_DATA_DIR")
    if env_dir:
        return Path(env_dir).expanduser().resolve()

    cwd = Path.cwd()
    for directory in (cwd, *cwd.parents):
        if _has_storage_hint(directory):
            return directory

    project_dir = Path(__file__).resolve().parent.parent
    return project_dir


def resolve_data_path(path_like: Union[str, os.PathLike]) -> Path:
    """Return absolute path for *path_like* within the storage directory."""

    path = Path(path_like)
    if path.is_absolute():
        return path
    base_dir = get_storage_dir()
    return base_dir / path


def load_json(filepath, default):
    """Load JSON data from *filepath* returning *default* on failure."""

    path = resolve_data_path(filepath)
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as file:
                return json.load(file)
        except json.JSONDecodeError:
            return default
    return default


def save_json(filepath, data):
    """Serialize *data* as JSON to *filepath* using UTF-8 encoding."""

    path = resolve_data_path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def load_domains():
    domains = load_json("domain.json", [])
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
    full_path = resolve_data_path(Path(history_dir) / filename)
    return str(full_path)


def delete_history_file(domain):
    history_filepath = resolve_data_path(history_file_path(domain))

    if history_filepath.exists():
        try:
            history_filepath.unlink()
            logger.info("Файл истории %s удалён.", history_filepath)
            return True
        except Exception as e:  # pragma: no cover - log path
            logger.error("Ошибка при удалении файла истории %s: %s", history_filepath, e)
            return False
    logger.warning("Файл истории %s не найден.", history_filepath)
    return True  # Считаем, что файл уже удалён

