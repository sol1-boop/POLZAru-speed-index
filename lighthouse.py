# lighthouse.py

import asyncio
import json
import logging
import os
import shlex
import shutil
import signal
import subprocess
import tempfile
from pathlib import Path
from uuid import uuid4

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HISTORY_DIR = 'history_files'
if not os.path.exists(HISTORY_DIR):
    os.makedirs(HISTORY_DIR)

try:
    from modules.config import load_config
except Exception:  # pragma: no cover - fallback for early bootstrap errors
    load_config = lambda: {}


def _normalize_command(candidate):
    """Return a list representation of *candidate* or ``None``."""
    if not candidate:
        return None
    if isinstance(candidate, (list, tuple)):
        return [str(part) for part in candidate if part]
    if isinstance(candidate, str):
        parts = shlex.split(candidate)
        return parts if parts else None
    return None


def _is_executable(command):
    """Check that the first item of *command* is executable."""
    if not command:
        return False
    executable = command[0]
    located = shutil.which(executable)
    if located:
        command[0] = located
        return True
    return Path(executable).exists()


def resolve_lighthouse_command():
    """Return command list to execute Lighthouse CLI."""
    env_candidate = _normalize_command(os.getenv('LIGHTHOUSE_PATH'))
    if env_candidate and _is_executable(env_candidate):
        return env_candidate

    config = load_config() or {}
    config_candidate = _normalize_command(
        config.get('lighthouse_cmd') or config.get('lighthouse_path')
    )
    if config_candidate and _is_executable(config_candidate):
        return config_candidate

    if os.name == 'nt':
        default = _normalize_command('lighthouse.cmd')
    else:
        default = _normalize_command('lighthouse')
    if default and _is_executable(default):
        return default

    project_root = Path(__file__).resolve().parent
    node_modules_cmd = project_root / 'node_modules' / '.bin'
    node_binary = 'lighthouse.cmd' if os.name == 'nt' else 'lighthouse'
    node_path = node_modules_cmd / node_binary
    node_candidate = _normalize_command(str(node_path))
    if node_candidate and _is_executable(node_candidate):
        return node_candidate

    npx_candidate = _normalize_command('npx lighthouse')
    if npx_candidate and _is_executable(npx_candidate):
        return npx_candidate

    return None


async def get_lighthouse_metrics(url: str, mobile: bool = False, headless: bool = True) -> dict:
    """Run lighthouse audit asynchronously."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        sync_get_lighthouse_metrics,
        url,
        mobile,
        headless,
    )

def cleanup_temp_chrome_data() -> None:
    """Remove stale Chrome temporary directories and caches."""
    try:
        temp_path = Path(tempfile.gettempdir())
        patterns = ("chrome-*", "chrome_profile_*")
        for pattern in patterns:
            for item in temp_path.glob(pattern):
                if item.is_dir():
                    shutil.rmtree(item, ignore_errors=True)
                else:
                    try:
                        item.unlink()
                    except FileNotFoundError:
                        pass

        home = Path.home()
        for profile in (home / ".config" / "Google" / "Chrome", home / ".config" / "chromium"):
            if profile.exists():
                shutil.rmtree(profile, ignore_errors=True)
    except Exception as e:
        logger.warning(f"Ошибка при очистке временных данных Chrome: {e}")


def create_temp_chrome_profile() -> str:
    """Create a unique temporary profile directory for Chrome."""
    profile_dir = Path(tempfile.gettempdir()) / f"chrome_profile_{uuid4().hex}"
    profile_dir.mkdir()
    return str(profile_dir)


def sync_get_lighthouse_metrics(url: str, mobile: bool = False, headless: bool = True) -> dict:
    cleanup_temp_chrome_data()
    profile_dir = create_temp_chrome_profile()
    try:
        command = resolve_lighthouse_command()
        if not command:
            logger.error(
                "Lighthouse CLI не найден. Установите lighthouse или укажите путь "
                "в переменной окружения LIGHTHOUSE_PATH либо ключе "
                "'lighthouse_path' файла config.json."
            )
            return {}

        chrome_flags = '--no-sandbox --incognito --disable-dev-shm-usage'
        if headless:
            chrome_flags += ' --headless --disable-gpu'
        chrome_flags += f' --user-data-dir={profile_dir}'
        max_wait_for_load = '--max-wait-for-load=450000'
        if mobile:
            chrome_flags += ' --window-size=412,823'
            lighthouse_flags = [
                *command,
                url,
                '--output=json',
                '--quiet',
                '--only-audits=first-contentful-paint,largest-contentful-paint,server-response-time,total-blocking-time,speed-index,interaction-to-next-paint,experimental-interaction-to-next-paint',
                '--emulated-form-factor=mobile',
                f'--chrome-flags={chrome_flags}',
                max_wait_for_load
            ]
        else:
            lighthouse_flags = [
                *command,
                url,
                '--output=json',
                '--quiet',
                '--only-audits=first-contentful-paint,largest-contentful-paint,server-response-time,total-blocking-time,speed-index,interaction-to-next-paint,experimental-interaction-to-next-paint',
                f'--chrome-flags={chrome_flags}',
                max_wait_for_load
            ]

        # Запускаем Lighthouse в новой группе процессов
        if os.name != 'nt':
            process = subprocess.Popen(
                lighthouse_flags,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                preexec_fn=os.setsid
            )
        else:
            process = subprocess.Popen(
                lighthouse_flags,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )

        try:
            stdout, stderr = process.communicate(timeout=300)  # Таймаут в секундах
        except subprocess.TimeoutExpired:
            logger.error(f"Превышено время ожидания (5 минут) при аудите {url}. Прерывание процесса.")
            # Завершаем процесс и его дочерние процессы
            if os.name != 'nt':
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            else:
                process.send_signal(signal.CTRL_BREAK_EVENT)
            stdout, stderr = process.communicate()
            return {}

        if process.returncode != 0:
            logger.error(f"Lighthouse вернул код ошибки {process.returncode} для {url}")
            logger.error(f"Сообщение об ошибке: {stderr}")
            return {}

        if stdout:
            result_json = json.loads(stdout)
            return result_json
        else:
            logger.error(f"Нет вывода от Lighthouse для {url}")
            return {}

    except json.JSONDecodeError as json_err:
        logger.error(f"Ошибка декодирования JSON для {url}: {json_err}")
        return {}
    except Exception as e:
        logger.exception(f"Ошибка при запуске Lighthouse для {url}: {e}")
        return {}
    finally:
        shutil.rmtree(profile_dir, ignore_errors=True)
        cleanup_temp_chrome_data()

async def main():
    # Ваш код для запуска аудита доменов без участия бота
    pass

if __name__ == '__main__':
    asyncio.run(main())
