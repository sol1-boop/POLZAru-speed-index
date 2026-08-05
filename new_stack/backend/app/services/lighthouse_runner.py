"""
Lighthouse Runner Service

Runs Lighthouse audits using Chrome in Docker environment.
Adapted from legacy lighthouse.py with improved error handling and cleanup.
"""

import asyncio
import json
import logging
import os
import shutil
import signal
import subprocess
import tempfile
from pathlib import Path
from uuid import uuid4
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class LighthouseRunner:
    """Service for running Lighthouse audits."""
    
    def __init__(self, chrome_flags: Optional[str] = None, timeout: int = 300):
        self.chrome_flags = chrome_flags or "--no-sandbox --incognito"
        self.timeout = timeout
        self.max_wait_for_load = 450000  # 7.5 minutes
        
    def _cleanup_temp_chrome_data(self) -> None:
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
            for profile in (
                home / ".config" / "Google" / "Chrome",
                home / ".config" / "chromium"
            ):
                if profile.exists():
                    shutil.rmtree(profile, ignore_errors=True)
        except Exception as e:
            logger.warning(f"Ошибка при очистке временных данных Chrome: {e}")

    def _create_temp_chrome_profile(self) -> str:
        """Create a unique temporary profile directory for Chrome."""
        profile_dir = Path(tempfile.gettempdir()) / f"chrome_profile_{uuid4().hex}"
        profile_dir.mkdir(parents=True, exist_ok=True)
        return str(profile_dir)

    async def run_audit(
        self,
        url: str,
        mobile: bool = False,
        headless: bool = True
    ) -> Dict[str, Any]:
        """
        Run Lighthouse audit for the given URL.
        
        Args:
            url: URL to audit
            mobile: Whether to use mobile emulation
            headless: Whether to run Chrome in headless mode
            
        Returns:
            Dictionary with audit results or empty dict on failure
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._sync_run_audit,
            url,
            mobile,
            headless,
        )

    def _sync_run_audit(
        self,
        url: str,
        mobile: bool = False,
        headless: bool = True
    ) -> Dict[str, Any]:
        """Synchronous Lighthouse audit execution."""
        self._cleanup_temp_chrome_data()
        profile_dir = self._create_temp_chrome_profile()
        
        try:
            # Determine Lighthouse path
            default_lighthouse_path = 'lighthouse.cmd' if os.name == 'nt' else 'lighthouse'
            lighthouse_path = os.getenv('LIGHTHOUSE_PATH', default_lighthouse_path)

            if not shutil.which(lighthouse_path):
                logger.error(f"Lighthouse не найден по пути: {lighthouse_path}")
                return {}

            # Build Chrome flags
            chrome_flags = self.chrome_flags
            if headless:
                chrome_flags += " --headless=new"
            chrome_flags += f" --user-data-dir={profile_dir}"
            
            if mobile:
                chrome_flags += " --window-size=412,823"

            # Build Lighthouse command
            only_audits = (
                "--only-audits=first-contentful-paint,largest-contentful-paint,"
                "server-response-time,total-blocking-time,speed-index,"
                "interaction-to-next-paint,experimental-interaction-to-next-paint"
            )
            
            lighthouse_flags = [
                lighthouse_path,
                url,
                "--output=json",
                "--quiet",
                only_audits,
                f"--chrome-flags={chrome_flags}",
                f"--max-wait-for-load={self.max_wait_for_load}",
            ]
            
            if mobile:
                lighthouse_flags.append("--emulated-form-factor=mobile")

            # Start process
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

            # Wait for completion
            try:
                stdout, stderr = process.communicate(timeout=self.timeout)
            except subprocess.TimeoutExpired:
                logger.error(f"Превышено время ожидания ({self.timeout}s) при аудите {url}")
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
                return self._parse_lighthouse_result(result_json, url, mobile)
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
            self._cleanup_temp_chrome_data()

    def _parse_lighthouse_result(
        self,
        result: Dict[str, Any],
        url: str,
        mobile: bool
    ) -> Dict[str, Any]:
        """Parse Lighthouse result into standardized format."""
        audits = result.get("audits", {})
        
        def get_metric_value(audit_id: str) -> Optional[Dict[str, Any]]:
            audit = audits.get(audit_id, {})
            return {
                "score": audit.get("score"),
                "displayValue": audit.get("displayValue"),
                "numericValue": audit.get("numericValue"),
            } if audit else None

        return {
            "url": url,
            "mobile": mobile,
            "timestamp": result.get("fetchTime", ""),
            "categories": {
                "performance": result.get("categories", {}).get("performance", {}).get("score"),
            },
            "audits": {
                "first-contentful-paint": get_metric_value("first-contentful-paint"),
                "largest-contentful-paint": get_metric_value("largest-contentful-paint"),
                "server-response-time": get_metric_value("server-response-time"),
                "total-blocking-time": get_metric_value("total-blocking-time"),
                "speed-index": get_metric_value("speed-index"),
                "interaction-to-next-paint": get_metric_value("interaction-to-next-paint"),
            },
            "raw_result": result,
        }


# Legacy compatibility function
async def get_lighthouse_metrics(
    url: str,
    mobile: bool = False,
    headless: bool = True
) -> Dict[str, Any]:
    """Legacy function for backward compatibility."""
    runner = LighthouseRunner()
    return await runner.run_audit(url, mobile, headless)
