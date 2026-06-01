from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from datetime import datetime
from app.database import Base
from pydantic import BaseModel

# --- Database Models ---

class Trade(Base):
    __tablename__ = "trades"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String)
    amount = Column(Float)

class UserAccount(Base):
    __tablename__ = "user_accounts"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True)

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer)
    type = Column(String)  # "DEPOSIT" or "WITHDRAWAL"
    amount = Column(Float)
    status = Column(String)
    reference_code = Column(String)

class TermsAgreement(Base):
    __tablename__ = "terms_agreements"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    agreed_at = Column(DateTime, default=datetime.utcnow)
    terms_version = Column(String)
    ip_address = Column(String)

class BinaryTrade(Base):
    __tablename__ = "binary_trades"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    symbol = Column(String)
    stake_amount = Column(Float)
    direction = Column(String) # "CALL" or "PUT"
    payout_multiplier = Column(Float)
    is_capped = Column(Boolean)
    status = Column(String, default="OPEN") # "OPEN", "WON", "LOST"
    created_at = Column(DateTime, default=datetime.utcnow)
