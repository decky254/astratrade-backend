from sqlalchemy import Column, Integer, Float, String, DateTime
from datetime import datetime
from .database import Base

class UserAccount(Base):
    __tablename__ = "user_accounts"
    id = Column(String, primary_key=True)
    balance = Column(Float, default=0.0)

class Trade(Base):
    __tablename__ = "trades"
    id = Column(Integer, primary_key=True)
    user_id = Column(String)
    ticker = Column(String)
    shares = Column(Integer)
    price_at_entry = Column(Float)
    status = Column(String, default="OPEN") # OPEN, CLOSED, LIQUIDATED
    timestamp = Column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(String)
    action = Column(String)
    amount = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
