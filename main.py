import asyncio
import os
import requests
from fastapi import FastAPI, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from . import models, database

app = FastAPI(title="AstraTrade Institutional Engine")

# Dependency for DB sessions
def get_db():
    db = database.SessionLocal()
    try: yield db
    finally: db.close()

# --- PAYMENT SERVICES (IntaSend) ---

def trigger_intasend_b2c(phone: str, amount: float, ref: str):
    url = "https://sandbox.intasend.com/api/v1/payouts/"
    headers = {"Authorization": f"Bearer {os.getenv('INTASEND_SECRET_KEY')}"}
    payload = {
        "currency": "KES", "amount": amount, "provider": "MPESA-B2C",
        "account_id": phone, "narrative": f"AstraTrade Payout: {ref}"
    }
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Payout gateway rejection.")
    return response.json()

@app.post("/api/v1/payments/deposit")
def initiate_deposit(user_id: str, phone: str, amount: float):
    # Triggers the STK Push to the user
    payload = {
        "amount": amount, "phone_number": phone, "api_ref": user_id,
        "currency": "KES"
    }
    headers = {"Authorization": f"Bearer {os.getenv('INTASEND_SECRET_KEY')}"}
    response = requests.post("https://sandbox.intasend.com/api/v1/payment/mpesa-stk-push/", json=payload, headers=headers)
    return response.json()

@app.post("/api/v1/payments/webhook")
async def intasend_webhook(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    # Ensure you verify the signature in production!
    user_id = data.get("invoice", {}).get("api_ref")
    amount = float(data.get("invoice", {}).get("net_amount", 0))
    
    if data.get("state") == "COMPLETE":
        with db.begin():
            user = db.query(models.UserAccount).filter(models.UserAccount.id == user_id).first()
            if user:
                user.balance += amount
                db.add(models.AuditLog(user_id=user_id, action="DEPOSIT_COMPLETE", amount=amount))
    return {"status": "ACKNOWLEDGED"}

@app.post("/api/v1/payments/withdraw")
def process_withdrawal(user_id: str, phone: str, amount: float, db: Session = Depends(get_db)):
    with db.begin():
        user = db.query(models.UserAccount).filter(models.UserAccount.id == user_id).first()
        if not user or user.balance < amount:
            raise HTTPException(status_code=400, detail="Insufficient funds")
        user.balance -= amount
        db.add(models.AuditLog(user_id=user_id, action="WITHDRAWAL_INITIATED", amount=amount))
    
    trigger_intasend_b2c(phone, amount, f"WD_{user_id}")
    return {"status": "SUCCESS"}

# --- TRADE EXECUTION ---

@app.post("/api/v1/trades/place")
def execute_trade(user_id: str, ticker: str, shares: int, db: Session = Depends(get_db)):
    with db.begin():
        user = db.query(models.UserAccount).filter(models.UserAccount.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        price = 16.50 # Real-time feed placeholder
        cost = price * shares
        if user.balance < cost:
            raise HTTPException(status_code=400, detail="Insufficient funds")
        
        user.balance -= cost
        db.add(models.Trade(user_id=user_id, ticker=ticker, shares=shares, price_at_entry=price))
        db.add(models.AuditLog(user_id=user_id, action="TRADE_BUY", amount=cost))
    return {"status": "SUCCESS"}

# --- AUTOMATED LIQUIDATION WATCHDOG ---

async def liquidation_watchdog():
    while True:
        db = database.SessionLocal()
        trades = db.query(models.Trade).filter(models.Trade.status == "OPEN").all()
        for trade in trades:
            # Liquidate if price drops 20%
            if 13.20 <= (trade.price_at_entry * 0.80): 
                with db.begin():
                    user = db.query(models.UserAccount).filter(models.UserAccount.id == trade.user_id).first()
                    if user:
                        user.balance += (13.20 * trade.shares)
                        trade.status = "LIQUIDATED"
        db.close()
        await asyncio.sleep(5)

@app.on_event("startup")
async def startup():
    asyncio.create_task(liquidation_watchdog())
