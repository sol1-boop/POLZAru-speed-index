"""General utility helpers for working with JSON and history files."""

import json
import logging
import os
import re
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


_INVALID_FILENAME_CHARS = re.compile(r"[^\w.-]+", re.UNICODE)
_UNDERSCORE_RUNS = re.compile(r"_+")


def _sanitize_history_name(domain: str) -> str:
    """Return a filesystem-safe identifier derived from *domain*."""

    normalized = domain.replace("http://", "").replace("https://", "")
    normalized = _INVALID_FILENAME_CHARS.sub("_", normalized)
    normalized = _UNDERSCORE_RUNS.sub("_", normalized).strip("._")
    return normalized or "domain"


def _legacy_history_filename(domain: str) -> str:
    """Return the legacy filename used for *domain* history files."""

    return (
        f"history_{domain.replace('http://', '').replace('https://', '').replace('/', '_')}.json"
    )


def _find_existing_history_file(directory: Path, sanitized_name: str) -> Path | None:
    """Return an existing history file in *directory* matching *sanitized_name*."""

    if not directory.exists():
        return None

    for candidate in directory.glob("history_*.json"):
        base_name = candidate.stem[len("history_"):]
        if _sanitize_history_name(base_name) == sanitized_name:
            return candidate
    return None


def history_file_path(domain, history_dir="history_files"):
    """Return path to history file for *domain* within *history_dir*."""

    history_directory = resolve_data_path(Path(history_dir))
    sanitized_name = _sanitize_history_name(domain)
    sanitized_path = history_directory / f"history_{sanitized_name}.json"
    if sanitized_path.exists():
        return str(sanitized_path)

    legacy_path = history_directory / _legacy_history_filename(domain)
    if legacy_path.exists():
        return str(legacy_path)

    discovered_path = _find_existing_history_file(history_directory, sanitized_name)
    if discovered_path is not None:
        return str(discovered_path)

    return str(sanitized_path)


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

