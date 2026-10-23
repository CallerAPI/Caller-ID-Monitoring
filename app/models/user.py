from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    api_key_hash = Column(String(64), unique=True, index=True, nullable=False)
    # Kept in plain text because the monitor must call the lookup API on the owner's behalf.
    api_key = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
