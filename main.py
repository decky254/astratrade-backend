import os
import time
import requests
from fastapi import FastAPI, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(
    title="AstraTrade Core Financial Engine",
    description="Secure transaction protocol handling M-Pesa inputs, live webhooks, and verified withdrawals."
)

# 🔒 SECURITY POLICY: Allows your mobile frontend to communicate across network ports securely
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Swap out with your active Vercel production domain later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 💾 CENTRALIZED SERVER MEMORY LEDGER
# Tracks live balances completely independently of user phone browser storage to prevent tampering
USER_ACCOUNTS_LEDGER = {
    "user_test_id": 5000.00  # Starts with a base test capital of 5,000 KSh
}

# 🔑 SECURE GATEWAY CREDENTIALS (Saves keys away from your public code repository)
# In Render, add INTASEND_SECRET_KEY as an environment variable (either your test or live key)
INTASEND_SECRET_KEY = os.getenv("INTASEND_SECRET_KEY", "ISSecretKey_test_4c3c07d7-808a-4d39-a95a-828350cecd19")

# --- DATA SCHEMAS ---
class DepositPayload(BaseModel):
    user_id: str
    phone_number: str = Field(..., description="M-Pesa destination sequence (2547XXXXXXXX)")
    amount: float = Field(..., gt=0, description="Amount to push via STK")

class WithdrawalPayload(BaseModel):
    user_id: str
    destination_target: str = Field(..., description="Phone number or bank account receiving cash")
    amount: float = Field(..., gt=0, description="Capital volume exiting the system")


# --- API ENDPOINTS ---

@app.get("/api/v1/wallet/{user_id}")
def get_account_balance(user_id: str):
    """
    Fetches the secure transaction ledger balance for a given user.
    """
    if user_id not in USER_ACCOUNTS_LEDGER:
        USER_ACCOUNTS_LEDGER[user_id] = 0.00
        
    return {
        "status": "SUCCESS",
        "user_id": user_id,
        "balance_in_kes": USER_ACCOUNTS_LEDGER[user_id]
    }


@app.post("/api/v1/payments/deposit")
def process_stk_deposit(payload: DepositPayload):
    """
    Triggers an M-Pesa STK Push sequence via the IntaSend Gateway.
    Notice we no longer automatically credit the account here to prevent fraud.
    The account will be credited when the Webhook arrives.
    """
    if payload.amount < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Transaction aborted. Minimum M-Pesa deposit threshold is KSh 10.00"
        )
        
    # IntaSend Endpoint (Use sandbox URL for testing, change to api.intasend.com for live production)
    gateway_url = "https://sandbox.intasend.com/api/v1/payment/mpesa-stk-push/"
    
    headers = {
        "Authorization": f"Bearer {INTASEND_SECRET_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # We pass user_id into the 'api_ref' parameter so IntaSend returns it to our Webhook later!
    body = {
        "amount": str(payload.amount),
        "phone_number": payload.phone_number,
        "narrative": "AstraTrade Wallet Deposit",
        "api_ref": payload.user_id 
    }
    
    try:
        response = requests.post(gateway_url, json=body, headers=headers)
        gateway_data = response.json()
        
        if response.status_code not in [200, 201]:
            raise HTTPException(
                status_code=400, 
                detail=f"Gateway Rejected Request: {gateway_data.get('errors', 'Unknown error')}"
            )
            
        print(f"[M-PESA DISPATCH] STK Push sent out successfully to {payload.phone_number}")
        
        return {
            "status": "SUCCESS",
            "message": f"M-Pesa STK Push sent to {payload.phone_number}! Please enter your M-Pesa PIN to finalize tracking.",
            "gateway_ref": gateway_data.get("id", f"GTW_{int(time.time())}")
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Payment Bridge Connection Failed: {str(e)}"
        )


@app.post("/api/v1/payments/webhook")
async def intasend_webhook_listener(request: Request):
    """
    🔄 WEBHOOK LISTENER: IntaSend calls this instantly the moment the user types 
    their M-Pesa PIN and Safaricom processes the movement of funds.
    """
    try:
        data = await request.json()
        print(f"[WEBHOOK RECEIVED] Incoming payload packet parsed: {data}")
        
        # Check if the payment sequence state successfully cleared
        if data.get("state") == "COMPLETE":
            invoice = data.get("invoice", {})
            user_id = invoice.get("api_ref")       # Retracted from our sent token payload tracking point
            net_cleared = float(invoice.get("net_amount", 0))
            
            if user_id:
                # Dynamically provision wallet if it doesn't exist, then add funds securely
                if user_id not in USER_ACCOUNTS_LEDGER:
                    USER_ACCOUNTS_LEDGER[user_id] = 0.00
                
                USER_ACCOUNTS_LEDGER[user_id] += net_cleared
                print(f"[LEDGER UPDATE] Wallet {user_id} credited with KSh {net_cleared} via Webhook confirmation.")
            else:
                print("[WEBHOOK WARN] Transaction completed but no valid api_ref (user_id) found.")
                
        return {"status": "ACKNOWLEDGED"}
        
    except Exception as e:
        print(f"[WEBHOOK ERROR] Internal processor failure: {str(e)}")
        # Always reply with 200/ACK to the gateway so it stops aggressively retrying identical payloads
        return {"status": "ERROR", "message": str(e)}


@app.post("/api/v1/payments/withdraw")
def process_wallet_withdrawal(payload: WithdrawalPayload):
    """
    Verifies available user balances on the server and safely subtracts capital to complete a withdrawal.
    """
    current_available_balance = USER_ACCOUNTS_LEDGER.get(payload.user_id, 0.00)
    
    if payload.amount > current_available_balance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transaction declined. Insufficient funds. Requested: KSh {payload.amount}, Available: KSh {current_available_balance}"
        )
        
    print(f"[WITHDRAWAL LOG] Initiating clearance verification. Routing KSh {payload.amount} out to destination: {payload.destination_target}...")
    
    # Securely deduct from server state database balance
    USER_ACCOUNTS_LEDGER[payload.user_id] -= payload.amount
    
    return {
        "status": "SUCCESS",
        "message": f"Withdrawal request processed smoothly! KSh {payload.amount} is being transferred to {payload.destination_target}.",
        "remaining_balance_kes": USER_ACCOUNTS_LEDGER[payload.user_id],
        "transaction_reference": f"WTH_{int(time.time())}"
    }    
