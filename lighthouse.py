# lighthouse.py

import asyncio
import logging
import subprocess
import json
import os
import signal
import shutil

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HISTORY_DIR = 'history_files'
if not os.path.exists(HISTORY_DIR):
    os.makedirs(HISTORY_DIR)

async def get_lighthouse_metrics(url: str, mobile: bool = False) -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, sync_get_lighthouse_metrics, url, mobile)

def sync_get_lighthouse_metrics(url: str, mobile: bool = False) -> dict:
    try:
        if os.name == 'nt':
            default_lighthouse_path = 'lighthouse.cmd'
        else:
            default_lighthouse_path = 'lighthouse'

        lighthouse_path = os.getenv('LIGHTHOUSE_PATH', default_lighthouse_path)

        if not shutil.which(lighthouse_path):
            logger.error(f"Lighthouse не найден по пути: {lighthouse_path}")
            return {}

        chrome_flags = '--no-sandbox --disable-dev-shm-usage --headless'
        max_wait_for_load = '--max-wait-for-load=450000'
        if mobile:
            chrome_flags += ' --window-size=412,823'
            lighthouse_flags = [
                lighthouse_path,
                url,
                '--output=json',
                '--quiet',
                '--only-audits=first-contentful-paint,largest-contentful-paint,server-response-time,total-blocking-time,speed-index',
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
                '--only-audits=first-contentful-paint,largest-contentful-paint,server-response-time,total-blocking-time',
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

async def main():
    # Ваш код для запуска аудита доменов без участия бота
    pass

if __name__ == '__main__':
    asyncio.run(main())
