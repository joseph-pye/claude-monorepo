"""Database setup and models."""

import os
from datetime import datetime, date

from sqlalchemy import create_engine, Column, Integer, String, Date, DateTime, Boolean, Text
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/commitments.db")

os.makedirs("data", exist_ok=True)
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Commitment(Base):
    __tablename__ = "commitments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)  # mortgage, insurance, subscription, etc.
    provider = Column(String, default="")
    expiry_date = Column(Date, nullable=False)
    amount = Column(String, default="")  # free-text, e.g. "£1,200/year"
    notes = Column(Text, default="")
    reminder_90_sent = Column(Boolean, default=False)
    reminder_30_sent = Column(Boolean, default=False)
    reminder_7_sent = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
