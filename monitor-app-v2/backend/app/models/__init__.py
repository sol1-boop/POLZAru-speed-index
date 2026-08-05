from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class User(Base):
    """User model for authentication."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    domains = relationship("Domain", back_populates="owner", cascade="all, delete-orphan")


class Domain(Base):
    """Domain model for monitoring."""
    __tablename__ = "domains"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    check_interval = Column(Integer, default=3600)  # seconds
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    owner = relationship("User", back_populates="domains")
    metrics = relationship("LighthouseMetric", back_populates="domain", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="domain", cascade="all, delete-orphan")


class LighthouseMetric(Base):
    """Lighthouse performance metrics."""
    __tablename__ = "lighthouse_metrics"

    id = Column(Integer, primary_key=True, index=True)
    domain_id = Column(Integer, ForeignKey("domains.id"), nullable=False)
    performance_score = Column(Float)
    accessibility_score = Column(Float)
    best_practices_score = Column(Float)
    seo_score = Column(Float)
    pwa_score = Column(Float)
    first_contentful_paint = Column(Float)  # ms
    largest_contentful_paint = Column(Float)  # ms
    time_to_interactive = Column(Float)  # ms
    total_blocking_time = Column(Float)  # ms
    cumulative_layout_shift = Column(Float)
    report_url = Column(Text, nullable=True)
    checked_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    domain = relationship("Domain", back_populates="metrics")


class Alert(Base):
    """Alert model for notifications."""
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    domain_id = Column(Integer, ForeignKey("domains.id"), nullable=False)
    alert_type = Column(String(50), nullable=False)  # 'performance', 'accessibility', etc.
    threshold = Column(Float, nullable=False)
    current_value = Column(Float, nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    domain = relationship("Domain", back_populates="alerts")
