# lighthouse.py

import asyncio
import logging
import subprocess
import json
import os
import signal
import shutil
import tempfile
from pathlib import Path
from uuid import uuid4

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HISTORY_DIR = 'history_files'
if not os.path.exists(HISTORY_DIR):
    os.makedirs(HISTORY_DIR)

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
        if os.name == 'nt':
            default_lighthouse_path = 'lighthouse.cmd'
        else:
            default_lighthouse_path = 'lighthouse'

        lighthouse_path = os.getenv('LIGHTHOUSE_PATH', default_lighthouse_path)

        if not shutil.which(lighthouse_path):
            logger.error(f"Lighthouse не найден по пути: {lighthouse_path}")
            return {}

        chrome_flags = '--no-sandbox --incognito'
        if headless:
            chrome_flags += ' --headless'
        chrome_flags += f' --user-data-dir={profile_dir}'
        max_wait_for_load = '--max-wait-for-load=450000'
        if mobile:
            chrome_flags += ' --window-size=412,823'
            lighthouse_flags = [
                lighthouse_path,
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
                lighthouse_path,
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
