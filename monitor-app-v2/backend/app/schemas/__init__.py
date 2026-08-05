from pydantic import BaseModel, EmailStr, HttpUrl, Field
from typing import Optional, List
from datetime import datetime


# Token schemas
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None


# User schemas
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class UserUpdate(BaseModel):
    password: Optional[str] = Field(None, min_length=6)
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    id: int
    is_active: bool
    is_admin: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Domain schemas
class DomainBase(BaseModel):
    url: HttpUrl
    name: Optional[str] = None
    check_interval: int = Field(default=3600, ge=300)  # minimum 5 minutes


class DomainCreate(DomainBase):
    pass


class DomainUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    check_interval: Optional[int] = Field(None, ge=300)


class DomainResponse(DomainBase):
    id: int
    owner_id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Lighthouse metrics schemas
class LighthouseMetricBase(BaseModel):
    performance_score: Optional[float] = Field(None, ge=0, le=100)
    accessibility_score: Optional[float] = Field(None, ge=0, le=100)
    best_practices_score: Optional[float] = Field(None, ge=0, le=100)
    seo_score: Optional[float] = Field(None, ge=0, le=100)
    pwa_score: Optional[float] = Field(None, ge=0, le=100)
    first_contentful_paint: Optional[float] = None
    largest_contentful_paint: Optional[float] = None
    time_to_interactive: Optional[float] = None
    total_blocking_time: Optional[float] = None
    cumulative_layout_shift: Optional[float] = None


class LighthouseMetricCreate(LighthouseMetricBase):
    domain_id: int


class LighthouseMetricResponse(LighthouseMetricBase):
    id: int
    domain_id: int
    report_url: Optional[str] = None
    checked_at: datetime

    class Config:
        from_attributes = True


# Alert schemas
class AlertBase(BaseModel):
    alert_type: str
    threshold: float
    message: str


class AlertCreate(AlertBase):
    domain_id: int
    current_value: float


class AlertResponse(AlertBase):
    id: int
    domain_id: int
    current_value: float
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Login schema
class LoginRequest(BaseModel):
    username: str
    password: str
