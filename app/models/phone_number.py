from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, JSON
from sqlalchemy.sql import func
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any
from app.db.base import Base

# SQLAlchemy Model
class PhoneNumber(Base):
    __tablename__ = "phone_numbers"

    id = Column(Integer, primary_key=True, index=True)
    number = Column(String, unique=True, index=True)
    description = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    entity_type = Column(String, default="UNKNOWN")
    business_name = Column(String, nullable=True)
    business_category = Column(String, nullable=True)
    business_industry = Column(String, nullable=True)
    business_location = Column(String, nullable=True)
    is_spam = Column(Boolean, default=False)
    spam_reports = Column(Integer, default=0)
    disabled = Column(Boolean, default=False)
    monitoring_frequency = Column(Integer, default=5)
    complaints = Column(JSON, nullable=True)

# Pydantic Schemas
class PhoneNumberBase(BaseModel):
    number: str = Field(..., description="Phone number in E.164 format")
    description: Optional[str] = Field(None, description="Optional description for the phone number")
    is_active: bool = Field(True, description="Whether the phone number is being monitored")
    monitoring_frequency: int = 5

class PhoneNumberCreate(PhoneNumberBase):
    pass

class PhoneNumberUpdate(PhoneNumberBase):
    number: Optional[str] = None
    is_active: Optional[bool] = None
    disabled: bool | None = None
    monitoring_frequency: int | None = None

class PhoneNumberSchema(PhoneNumberBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    entity_type: str
    business_name: Optional[str] = None
    business_category: Optional[str] = None
    business_industry: Optional[str] = None
    business_location: Optional[str] = None
    is_spam: bool
    spam_reports: int
    disabled: bool
    complaints: Optional[List[Dict[str, Any]]] = None

    class Config:
        from_attributes = True