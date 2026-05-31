from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from app.database import Base

# --- Database Models (Tables) ---

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
    status = Column(String)  # "PENDING" or "COMPLETED"
    reference_code = Column(String)

class TermsAgreement(Base):
    __tablename__ = "terms_agreements"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)  # Links to the UserAccount
    agreed_at = Column(DateTime, default=datetime.utcnow)  # Timestamp of agreement
    terms_version = Column(String)  # To track which version they accepted
    ip_address = Column(String)  # Audit log for the connection origin

# --- Pydantic Schemas (For API Data Validation) ---

from pydantic import BaseModel

class TradeCreate(BaseModel):
    symbol: str
    amount: float

class TransactionCreate(BaseModel):
    user_id: int
    type: str
    amount: float
