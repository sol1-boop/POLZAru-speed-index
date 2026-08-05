"""
Telegram Notification Service

Sends alerts to Telegram channel.
Adapted from legacy alerts.py with improved error handling.
"""

import logging
from typing import Optional, List, Dict, Any

import httpx

logger = logging.getLogger(__name__)


class TelegramService:
    """Service for sending notifications to Telegram."""
    
    def __init__(
        self,
        bot_token: str,
        chat_id: str,
        api_url: str = "https://api.telegram.org/bot"
    ):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"{api_url}{bot_token}/sendMessage"
        
    async def send_alert(
        self,
        message: str,
        parse_mode: str = "HTML"
    ) -> bool:
        """
        Send alert message to Telegram channel.
        
        Args:
            message: Message text (supports HTML markup)
            parse_mode: Parse mode (HTML or Markdown)
            
        Returns:
            True if sent successfully, False otherwise
        """
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": parse_mode,
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.api_url, data=payload)
                response.raise_for_status()
                
            logger.info(f"Alert sent to Telegram: {message[:50]}...")
            return True
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error sending Telegram alert: {e}")
            return False
        except Exception as e:
            logger.exception(f"Error sending Telegram alert: {e}")
            return False

    async def send_exceedance_alerts(
        self,
        exceedances: List[Dict[str, Any]]
    ) -> int:
        """
        Send alerts for budget exceedances.
        
        Args:
            exceedances: List of exceedance dictionaries from BudgetService
            
        Returns:
            Number of successfully sent alerts
        """
        sent_count = 0
        
        for item in exceedances:
            domain_url = item.get("domain_url", "Unknown")
            exceeded_metrics = item.get("exceeded_metrics", {})
            
            # Format message
            message = f"⚠️ <b>Алерт для {domain_url}</b> ⚠️\n\n"
            
            for metric, data in exceeded_metrics.items():
                actual = data.get("actual", "N/A")
                budget = data.get("budget", "N/A")
                
                # Format metric name for display
                metric_display = metric.replace("-", " ").title()
                
                message += f"{metric_display}: {actual:.2f}s (бюджет: {budget:.2f}s)\n"
            
            message += f"\n⏰ {item.get('timestamp', '')}"
            
            if await self.send_alert(message):
                sent_count += 1
        
        return sent_count

    async def send_audit_started(
        self,
        url: str,
        mobile: bool = False
    ) -> bool:
        """Send notification that audit has started."""
        device = "📱 Mobile" if mobile else "💻 Desktop"
        message = f"{device} Начинаем аудит для: {url}"
        return await self.send_alert(message)

    async def send_audit_result(
        self,
        url: str,
        metrics: Dict[str, Any],
        mobile: bool = False
    ) -> bool:
        """Send audit results to Telegram."""
        device = "📱 Mobile" if mobile else "💻 Desktop"
        
        message = f"{device} Результаты аудита для {url}:\n\n"
        
        metric_names = {
            "fcp": "FCP",
            "lcp": "LCP",
            "ttfb": "TTFB",
            "tbt": "TBT",
            "speed_index": "Speed Index",
            "inp": "INP",
        }
        
        for key, display_name in metric_names.items():
            value = metrics.get(key)
            if value is not None:
                message += f"{display_name}: {value:.2f}s\n"
            else:
                message += f"{display_name}: N/A\n"
        
        return await self.send_alert(message)

    async def send_error_notification(
        self,
        error_message: str,
        context: Optional[str] = None
    ) -> bool:
        """Send error notification."""
        message = f"❌ <b>Ошибка</b>\n\n{error_message}"
        if context:
            message += f"\n\nКонтекст: {context}"
        return await self.send_alert(message)


def get_telegram_service() -> Optional[TelegramService]:
    """
    Factory function to create TelegramService from environment variables.
    
    Returns:
        TelegramService instance or None if configuration is missing
    """
    import os
    
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        logger.warning("Telegram credentials not configured")
        return None
    
    return TelegramService(bot_token=token, chat_id=chat_id)
