from sqlalchemy import Column, Integer, String, Float
from pydantic import BaseModel
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

# --- Pydantic Schemas (For API Data Validation) ---

class TradeCreate(BaseModel):
    symbol: str
    amount: float

class TransactionCreate(BaseModel):
    user_id: int
    type: str  # "DEPOSIT" or "WITHDRAWAL"
    amount: float
