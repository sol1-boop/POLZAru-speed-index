from typing import Optional, Any, Dict
from pydantic import BaseModel


class ResponseModel(BaseModel):
    """Универсальная модель ответа API."""
    status: str
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
