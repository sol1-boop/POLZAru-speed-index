from pydantic import BaseModel, EmailStr, Field, HttpUrl
from typing import Optional
from datetime import datetime


# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    is_active: bool = True


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8)
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Token Schemas
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    email: Optional[str] = None


# Domain Schemas
class DomainBase(BaseModel):
    url: HttpUrl
    name: Optional[str] = None
    check_interval_minutes: int = Field(default=60, ge=5, le=1440)


class DomainCreate(DomainBase):
    pass


class DomainUpdate(BaseModel):
    url: Optional[HttpUrl] = None
    name: Optional[str] = None
    is_active: Optional[bool] = None
    check_interval_minutes: Optional[int] = Field(None, ge=5, le=1440)


class DomainResponse(DomainBase):
    id: int
    owner_id: int
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Lighthouse Metric Schemas
class LighthouseMetricBase(BaseModel):
    performance_score: Optional[float] = Field(None, ge=0, le=100)
    accessibility_score: Optional[float] = Field(None, ge=0, le=100)
    best_practices_score: Optional[float] = Field(None, ge=0, le=100)
    seo_score: Optional[float] = Field(None, ge=0, le=100)
    pwa_score: Optional[float] = Field(None, ge=0, le=100)
    first_contentful_paint: Optional[float] = None
    largest_contentful_paint: Optional[float] = None
    total_blocking_time: Optional[float] = None
    cumulative_layout_shift: Optional[float] = None
    speed_index: Optional[float] = None


class LighthouseMetricCreate(LighthouseMetricBase):
    domain_id: int
    report_url: Optional[str] = None
    screenshot_path: Optional[str] = None


class LighthouseMetricResponse(LighthouseMetricBase):
    id: int
    domain_id: int
    report_url: Optional[str] = None
    checked_at: datetime

    class Config:
        from_attributes = True


# Alert Schemas
class AlertBase(BaseModel):
    metric_name: str
    threshold_value: float
    current_value: float
    severity: str = "warning"
    message: Optional[str] = None


class AlertCreate(AlertBase):
    domain_id: int


class AlertResponse(AlertBase):
    id: int
    domain_id: int
    is_resolved: bool
    created_at: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Dashboard / Summary Schema
class DashboardSummary(BaseModel):
    total_domains: int
    active_domains: int
    total_checks: int
    alerts_count: int
    avg_performance_score: Optional[float] = None
