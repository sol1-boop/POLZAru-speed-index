from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    domains = relationship("Domain", back_populates="owner", cascade="all, delete-orphan")


class Domain(Base):
    __tablename__ = "domains"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    check_interval_minutes = Column(Integer, default=60)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    owner = relationship("User", back_populates="domains")
    metrics = relationship("LighthouseMetric", back_populates="domain", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="domain", cascade="all, delete-orphan")


class LighthouseMetric(Base):
    __tablename__ = "lighthouse_metrics"

    id = Column(Integer, primary_key=True, index=True)
    domain_id = Column(Integer, ForeignKey("domains.id"), nullable=False)
    
    # Scores (0-100)
    performance_score = Column(Float)
    accessibility_score = Column(Float)
    best_practices_score = Column(Float)
    seo_score = Column(Float)
    pwa_score = Column(Float)
    
    # Detailed metrics
    first_contentful_paint = Column(Float)  # ms
    largest_contentful_paint = Column(Float)  # ms
    total_blocking_time = Column(Float)  # ms
    cumulative_layout_shift = Column(Float)
    speed_index = Column(Float)  # ms
    
    # Report
    report_url = Column(Text, nullable=True)
    screenshot_path = Column(String, nullable=True)
    
    checked_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    domain = relationship("Domain", back_populates="metrics")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    domain_id = Column(Integer, ForeignKey("domains.id"), nullable=False)
    metric_name = Column(String, nullable=False)
    threshold_value = Column(Float, nullable=False)
    current_value = Column(Float, nullable=False)
    severity = Column(String, default="warning")  # info, warning, critical
    message = Column(Text)
    is_resolved = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    domain = relationship("Domain", back_populates="alerts")
