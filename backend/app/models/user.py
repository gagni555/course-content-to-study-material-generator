from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from app.models.database import Base
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=True)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    tier = Column(String, default="free")  # free, premium, etc.
    api_usage_current = Column(Integer, default=0)  # Track token usage
    api_usage_limit = Column(Integer, default=50000)  # Max tokens per day for free tier


class UserCreate(BaseModel):
    email: str
    username: Optional[str] = None
    full_name: Optional[str] = None
    password: str


class UserUpdate(BaseModel):
    username: Optional[str] = None
    full_name: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    email: str
    username: Optional[str]
    full_name: Optional[str]
    is_active: bool
    is_verified: bool
    created_at: datetime
    tier: str
    api_usage_current: int
    api_usage_limit: int

    class Config:
        from_attributes = True