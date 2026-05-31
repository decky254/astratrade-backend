import asyncio
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from . import models, database

app = FastAPI(title="AstraTrade Institutional Engine")

def get_db():
    db = database.SessionLocal()
    try: yield db
    finally: db.close()

# --- ATOMIC TRADE EXECUTION ---
@app.post("/api/v1/trades/place")
def execute_trade(user_id: str, ticker: str, shares: int, db: Session = Depends(get_db)):
    try:
        with db.begin(): # Start ACID Transaction
            user = db.query(models.UserAccount).filter(models.UserAccount.id == user_id).one()
            # Simulation: Replace with real-time price fetch
            price = 16.50 
            cost = price * shares
            
            if user.balance < cost:
                raise HTTPException(status_code=400, detail="Insufficient funds")
            
            user.balance -= cost
            db.add(models.Trade(user_id=user_id, ticker=ticker, shares=shares, price_at_entry=price))
            db.add(models.AuditLog(user_id=user_id, action="TRADE_BUY", amount=cost))
            
        return {"status": "SUCCESS", "new_balance": user.balance}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Transaction failed; state rolled back.")

# --- LIQUIDATION WATCHDOG ---
async def liquidation_watchdog():
    while True:
        db = database.SessionLocal()
        trades = db.query(models.Trade).filter(models.Trade.status == "OPEN").all()
        for trade in trades:
            # Logic: If price drops below 80% of entry, liquidate
            if 15.00 <= (trade.price_at_entry * 0.80): 
                with db.begin():
                    user = db.query(models.UserAccount).get(trade.user_id)
                    user.balance += (15.00 * trade.shares)
                    trade.status = "LIQUIDATED"
        db.close()
        await asyncio.sleep(5)

@app.on_event("startup")
async def startup():
    # Ensure tables exist
    models.Base.metadata.create_all(bind=database.engine)
    # Start background task
    asyncio.create_task(liquidation_watchdog())
