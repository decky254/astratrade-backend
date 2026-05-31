from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app import models, database
from app.models import Trade, TradeCreate

# Create tables in DB
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI()

# Add CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database Dependency
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"message": "AstraTrade API is live!"}

@app.post("/trades/")
def create_trade(trade: TradeCreate, db: Session = Depends(get_db)):
    new_trade = Trade(symbol=trade.symbol, amount=trade.amount)
    db.add(new_trade)
    db.commit()
    db.refresh(new_trade)
    return {"message": "Trade saved successfully!", "trade_id": new_trade.id}
