from sqlalchemy import Column, Integer, String, Float
from pydantic import BaseModel
from app.database import Base

# Database Models
class Trade(Base):
    __tablename__ = "trades"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String)
    amount = Column(Float)

class UserAccount(Base):
    __tablename__ = "user_accounts"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True)

# Pydantic Schemas for API Communication
class TradeCreate(BaseModel):
    symbol: str
    amount: float
