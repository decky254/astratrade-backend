from fastapi import FastAPI, Request, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, database, schemas

app = FastAPI()

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Registration Route (Maintains ToS) ---
@app.post("/register/")
def register_user(user: schemas.UserCreate, request: Request, db: Session = Depends(get_db)):
    new_user = models.UserAccount(username=user.username)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Log ToS agreement
    new_agreement = models.TermsAgreement(
        user_id=new_user.id,
        terms_version="v1.0",
        ip_address=request.client.host
    )
    db.add(new_agreement)
    db.commit()
    return {"message": "User registered and terms accepted."}

# --- Binary Trading Route (Maintains House Edge & Caps) ---
@app.post("/trade/binary/")
def place_binary_trade(user_id: int, symbol: str, stake: float, direction: str, db: Session = Depends(get_db)):
    multiplier = 3.2
    potential_payout = stake * multiplier
    
    # Apply House Protection Cap (5000 KES limit)
    is_capped = potential_payout > 5000.0
    final_payout = 5000.0 if is_capped else potential_payout
        
    new_trade = models.BinaryTrade(
        user_id=user_id, symbol=symbol, stake_amount=stake,
        direction=direction, payout_multiplier=multiplier,
        is_capped=is_capped, status="OPEN"
    )
    db.add(new_trade)
    db.commit()
    return {"status": "success", "payout": final_payout, "capped": is_capped}

# --- History View Route ---
@app.get("/history/{user_id}/")
def get_user_history(user_id: int, db: Session = Depends(get_db)):
    trades = db.query(models.BinaryTrade).filter(models.BinaryTrade.user_id == user_id).all()
    return {"history": trades}
