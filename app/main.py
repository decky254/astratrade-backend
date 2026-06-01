import os
import time
import hmac
import hashlib
import random
from typing import Dict, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from fastapi import FastAPI, Request, HTTPException, status, Header
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Astra Trade - Synthetic Trading Engine Backend",
    version="2.1.0",
    description="Unified core backend for Astra Trade, covering spot locks, binary option constraints, and secure cryptographic IntaSend webhooks."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 🔑 SECURITY CREDENTIAL CONFIGURATION
# ==========================================
# Read from environment variables for production security (Render environment variables)
# Fallback to a development key string only for your ThinkPad local environment testing
INTASEND_SECRET_KEY = os.getenv("INTASEND_SECRET_KEY", "ISSecretKey-your-sandbox-or-live-secret-token-here")

# ==========================================
# 💾 STATEFUL IN-MEMORY SYSTEM LEDGERS 
# ==========================================
USER_ACCOUNTS_LEDGER: Dict[str, float] = {}
TERMS_AGREEMENTS_LOG: Dict[str, dict] = {}
BINARY_OPTIONS_LEDGER: Dict[str, dict] = {}
USER_REFERRAL_CODES: Dict[str, str] = {}            
REFERRAL_AFFILIATION_MAP: Dict[str, str] = {}       

# Seed mock database record
USER_ACCOUNTS_LEDGER["usr_test_alpha"] = 2037.00
USER_REFERRAL_CODES["usr_test_alpha"] = "ASTRA_MARK_742"

# ==========================================
# 📊 DATA VALIDATION SCHEMAS (PYDANTIC)
# ==========================================
class RegisterPayload(BaseModel):
    username: str
    referral_code: Optional[str] = Field(None, description="Optional invite string shared by an Astra Trade promoter")

class BinaryWagerPayload(BaseModel):
    user_id: str
    symbol: str = Field(..., description="Target stock symbol ticker (e.g., SCOM, EQTY)")
    stake: float = Field(..., gte=10.0, description="Wager amount in KSh")
    direction: str = Field(..., description="Must be either 'CALL' (RISE) or 'PUT' (FALL)")

# ==========================================
# 🔐 AUTHENTICATION & VIRAL ONBOARDING ENGINE
# ==========================================
@app.post("/api/v1/auth/register", status_code=status.HTTP_201_CREATED)
def register_and_accept_terms(payload: RegisterPayload, request: Request):
    generated_user_id = f"usr_{int(time.time())}_{random.randint(100, 999)}"
    
    if payload.username.strip() == "":
        raise HTTPException(status_code=400, detail="Username field cannot be blank.")
        
    USER_ACCOUNTS_LEDGER[generated_user_id] = 0.00
    
    clean_name_prefix = "".join(ch for ch in payload.username.upper() if ch.isalnum())[:4]
    personal_promo_token = f"ASTRA_{clean_name_prefix}_{random.randint(100, 999)}"
    USER_REFERRAL_CODES[generated_user_id] = personal_promo_token
    
    if payload.referral_code:
        target_code = payload.referral_code.strip().upper()
        referrer_id = None
        
        for uid, code in USER_REFERRAL_CODES.items():
            if code == target_code:
                referrer_id = uid
                break
        
        if referrer_id and referrer_id != generated_user_id:
            REFERRAL_AFFILIATION_MAP[generated_user_id] = referrer_id
            print(f"🔗 [ASTRA LINKED] Account {generated_user_id} tracked to Inviter {referrer_id}")

    client_ip = request.client.host if request.client else "127.0.0.1"
    TERMS_AGREEMENTS_LOG[generated_user_id] = {
        "agreed_at": datetime.utcnow().isoformat(),
        "terms_version": "v1.2",
        "ip_address": client_ip
    }
    
    return {
        "status": "SUCCESS",
        "user_id": generated_user_id,
        "personal_referral_code": personal_promo_token,
        "message": "Astra Trade profile initialized. Mandatory Terms of Service consent recorded successfully."
    }

# ==========================================
# 📊 SPECULATIVE BINARY EXECUTION CONTROLLER
# ==========================================
@app.post("/api/v1/trades/binary/wager")
def place_binary_prediction_contract(payload: BinaryWagerPayload):
    if payload.user_id not in USER_ACCOUNTS_LEDGER:
        raise HTTPException(status_code=404, detail="User account profile sequence identifier not found.")
    
    clean_direction = payload.direction.strip().upper()
    if clean_direction not in ["CALL", "PUT"]:
        raise HTTPException(status_code=400, detail="Invalid direction. Must be CALL or PUT.")
        
    current_balance = USER_ACCOUNTS_LEDGER[payload.user_id]
    if payload.stake > current_balance:
        raise HTTPException(status_code=400, detail="Insufficient clearing liquidity for trade execution.")
    
    USER_ACCOUNTS_LEDGER[payload.user_id] -= payload.stake
    
    MULTIPLIER = 3.2
    EXPOSURE_CEILING = 5000.00
    
    raw_payout = payload.stake * MULTIPLIER
    is_capped = raw_payout > EXPOSURE_CEILING
    final_allowable_payout = EXPOSURE_CEILING if is_capped else raw_payout
    
    contract_id = f"ast_bin_{int(time.time())}_{random.randint(1000, 9999)}"
    
    BINARY_OPTIONS_LEDGER[contract_id] = {
        "user_id": payload.user_id,
        "symbol": payload.symbol.upper(),
        "stake": payload.stake,
        "direction": clean_direction,
        "potential_payout": final_allowable_payout,
        "is_capped": is_capped,
        "status": "OPEN",
        "created_at": datetime.utcnow().isoformat()
    }
    
    return {
        "status": "SUCCESS",
        "trade_id": contract_id,
        "deducted_stake": payload.stake,
        "remaining_balance": USER_ACCOUNTS_LEDGER[payload.user_id],
        "potential_return": final_allowable_payout,
        "exposure_capped": is_capped
    }

# ==========================================
# 📜 CONTRACT RESOLUTION & HISTORICAL LOGS
# ==========================================
@app.get("/api/v1/trades/binary/history/{user_id}")
def get_binary_options_history(user_id: str):
    if user_id not in USER_ACCOUNTS_LEDGER:
        raise HTTPException(status_code=404, detail="Profile record target tracker matching given identifier does not exist.")
        
    user_historical_records = []
    TRUE_WIN_PROBABILITY = 0.20  
    
    for trade_id, trade_data in BINARY_OPTIONS_LEDGER.items():
        if trade_data["user_id"] == user_id:
            if trade_data["status"] == "OPEN":
                rng_draw = random.random()
                if rng_draw <= TRUE_WIN_PROBABILITY:
                    trade_data["status"] = "WON"
                    USER_ACCOUNTS_LEDGER[user_id] += trade_data["potential_payout"]
                else:
                    trade_data["status"] = "LOST"
            
            user_historical_records.append({
                "trade_id": trade_id,
                "symbol": trade_data["symbol"],
                "stake": trade_data["stake"],
                "direction": trade_data["direction"],
                "payout": trade_data["potential_payout"] if trade_data["status"] == "WON" else 0.00,
                "is_capped": trade_data["is_capped"],
                "status": trade_data["status"],
                "created_at": trade_data["created_at"]
            })
            
    return sorted(user_historical_records, key=lambda x: x["created_at"], reverse=True)

# ==========================================
# 💳 SECURE INTA-SEND WEBHOOK ENGINE (UPDATED)
# ==========================================
@app.post("/api/v1/payments/intasend-callback")
async def intasend_webhook_listener(request: Request, x_intasend_digest: Optional[str] = Header(None)):
    """
    Clears incoming mobile/card cash flows, runs SHA256 signature verification 
    via the secret token tracking, and hooks directly into double-sided referral modules.
    """
    # 1. Read the raw request body data string for verification hashing
    raw_body = await request.body()
    
    # 2. Security Check: Enforce secret signature verification protocol
    if not x_intasend_digest:
        print("🛑 [SECURITY BRIEF] Webhook rejected. IntaSend validation digest string header missing.")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authorization tracking vector signature.")
    
    # Generate an explicit HMAC-SHA256 signature hash from the incoming data stream using our tracking token
    computed_hmac = hmac.new(
        bytes(INTASEND_SECRET_KEY, 'utf-8'),
        msg=raw_body,
        digestmod=hashlib.sha256
    )
    expected_digest = computed_hmac.hexdigest()
    
    # Secure string comparison mechanism to defeat timing exploits
    if not hmac.compare_digest(expected_digest, x_intasend_digest):
        print("🛑 [SECURITY ALTERCATION] Webhook dropped! Received data digest string does not match local verification token keys.")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook transaction signature validation tokens.")

    # 3. Securely Parse JSON values once the transaction data path is fully authenticated
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed JSON data array structure parsing error.")
        
    invoice_id = payload.get("invoice_id")
    state = payload.get("state")
    net_cleared = float(payload.get("net_amount", 0.00))
    
    meta_data = payload.get("meta", {})
    user_id = meta_data.get("user_id") if isinstance(meta_data, dict) else None
    
    if not invoice_id or not state:
        raise HTTPException(status_code=422, detail="Missing critical internal invoice attributes mapping protocols.")
        
    if state == "COMPLETE" and user_id:
        if user_id not in USER_ACCOUNTS_LEDGER:
            USER_ACCOUNTS_LEDGER[user_id] = 0.00
            
        is_first_deposit = (USER_ACCOUNTS_LEDGER[user_id] == 0.00)
        USER_ACCOUNTS_LEDGER[user_id] += net_cleared
        print(f"💰 [ASTRA WALLET SIGNED & UPDATED] Account {user_id} topped up by KSh {net_cleared}.")
        
        if is_first_deposit and net_cleared >= 250.00 and user_id in REFERRAL_AFFILIATION_MAP:
            parent_referrer = REFERRAL_AFFILIATION_MAP[user_id]
            
            USER_ACCOUNTS_LEDGER[parent_referrer] += 50.00
            USER_ACCOUNTS_LEDGER[user_id] += 20.00
            
            print(f"🎉 [ASTRA VIRAL ACTIVATION] Inviter {parent_referrer} earned KSh 50. New User {user_id} earned KSh 20.")
            
    return {"status": "ACKNOWLEDGED", "processed_at": datetime.utcnow().isoformat()}

# ==========================================
# 🔍 DIAGNOSTIC SYSTEM OVERVIEW LOGS
# ==========================================
@app.get("/api/v1/system/status")
def global_system_sanity_check():
    return {
        "app_name": "Astra Trade Engine",
        "active_users_count": len(USER_ACCOUNTS_LEDGER),
        "tracked_affiliate_connections": len(REFERRAL_AFFILIATION_MAP),
        "settled_binary_contracts_total": len(BINARY_OPTIONS_LEDGER),
        "server_time_utc": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
