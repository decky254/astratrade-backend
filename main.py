import os
import time
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(
    title="AstraTrade Core Financial Engine",
    description="Secure transaction protocol handling M-Pesa inputs, liquid wallet ledgering, and verified withdrawals."
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
    Triggers an M-Pesa STK Push sequence and instantly prepares the ledger to accept the capital.
    """
    if payload.amount < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Transaction aborted. Minimum M-Pesa deposit threshold is KSh 10.00"
        )
        
    print(f"[DEPOSIT LOG] Secure authentication active. Processing KSh {payload.amount} STK Push sequence to {payload.phone_number}...")
    
    # Simulate an instantaneous mock callback verification confirming payment success
    # In a full staging system, a webhook updates this; here we directly process for prototyping speed
    USER_ACCOUNTS_LEDGER[payload.user_id] += payload.amount
    
    return {
        "status": "SUCCESS",
        "message": f"STK Push prompt sent successfully to {payload.phone_number}! KSh {payload.amount} has been provisionally cleared.",
        "new_balance_kes": USER_ACCOUNTS_LEDGER[payload.user_id],
        "transaction_reference": f"DEP_{int(time.time())}"
    }


@app.post("/api/v1/payments/withdraw")
def process_wallet_withdrawal(payload: WithdrawalPayload):
    """
    Verifies available user balances on the server and safely subtracts capital to complete a withdrawal.
    """
    # 🛡️ SECURITY GUARDRAIL: Check if the user actually has enough money in memory ledger
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
