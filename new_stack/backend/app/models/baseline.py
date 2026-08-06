from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class Baseline(Base):
    __tablename__ = "baselines"
    
    id = Column(Integer, primary_key=True, index=True)
    domain_id = Column(Integer, ForeignKey("domains.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    performance_score = Column(Float, default=0.0)
    lcp = Column(Float, default=0.0)
    fid = Column(Float, default=0.0)
    cls = Column(Float, default=0.0)
    fcp = Column(Float, default=0.0)
    tti = Column(Float, default=0.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    domain = relationship("Domain", back_populates="baselines")
    creator = relationship("User", back_populates="baselines")
