from fastapi import FastAPI, Request, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, database

app = FastAPI()

# Dependency to get DB session
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/register/")
def register_user(user: schemas.UserCreate, request: Request, db: Session = Depends(get_db)):
    # 1. Check if user already exists
    existing_user = db.query(models.UserAccount).filter(models.UserAccount.username == user.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    # 2. Create the user
    new_user = models.UserAccount(username=user.username)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # 3. Log the Terms of Service agreement
    # We capture the client's IP from the request object
    client_ip = request.client.host if request.client else "unknown"
    
    new_agreement = models.TermsAgreement(
        user_id=new_user.id,
        terms_version="v1.0",  # Increment this when you update your legal terms
        ip_address=client_ip
    )
    
    db.add(new_agreement)
    db.commit()
    
    return {"message": "User registered and terms accepted successfully."}
