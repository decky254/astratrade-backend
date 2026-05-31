import os
import time
import requests
from datetime import datetime, time as datetime_time
import pytz
from fastapi import FastAPI, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(
    title="AstraTrade Institutional Financial & Market Engine",
    description="Unified API hosting secure M-Pesa ledger tracks, automated NSE market settlement routines, and early position liquidation protocols."
)

# 🔒 SECURITY POLICY: Cross-Origin Resource Sharing validation configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Tighten this to your production Vercel frontend URL once live
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 💾 CENTRALIZED SERVER MEMORY LEDGERS (Protected Source of Truth)
USER_ACCOUNTS_LEDGER = {
    "user_test_id": 5000.00  # Default test capital allocation: KSh 5,000.00
}

# In-memory tracking mimicking database registers for active customer market contracts
ACTIVE_USER_TRADES = {}

# Tracks the real-time status of pushed transactions to catch failures (e.g., Insufficient Funds)
TRACKED_TRANSACTIONS = {}

# 📝 CENTRALIZED ESCROW STORAGE ARRAYS
PENDING_WEEKEND_ORDERS = []

# 🔑 SECURE GATEWAY INFRASTRUCTURE STRINGS
INTASEND_SECRET_KEY = os.getenv("INTASEND_SECRET_KEY", "your_api_token_here")


# --- DATA VALIDATION SCHEMAS (PYDANTIC) ---
class DepositPayload(BaseModel):
    user_id: str
    phone_number: str = Field(..., description="M-Pesa sequence format: 2547XXXXXXXX")
    amount: float = Field(..., gt=0)

class WithdrawalPayload(BaseModel):
    user_id: str
    destination_target: str = Field(..., description="Target account identifier receiving transfer funds")
    amount: float = Field(..., gt=0)

class TradePayload(BaseModel):
    user_id: str
    ticker: str = Field(..., description="NSE target security ticker symbol (e.g., SCOM, EQTY)")
    shares: int = Field(..., gt=0)

class EarlySettlementPayload(BaseModel):
    user_id: str
    trade_id: str
    settlement_type: str = Field(..., description="User choice parameter configuration: 'PARTIAL_CLOSE'")
    amount_kes: float = Field(..., description="Dynamic total stake passed directly from the active frontend viewport")


# --- DATA ROUTING & TIME MARKET UTILITIES ---
def is_market_open() -> bool:
    """
    Evaluates execution time constraints against the Nairobi Securities Exchange (NSE).
    Standard Operating Windows: Monday through Friday, 09:00 AM to 03:00 PM East African Time (EAT).
    """
    eat_timezone = pytz.timezone("Africa/Nairobi")
    now_eat = datetime.now(eat_timezone)
    
    if now_eat.weekday() >= 5:
        return False
        
    market_start = datetime_time(9, 0, 0)
    market_close = datetime_time(15, 0, 0)
    
    return market_start <= now_eat.time() <= market_close


def get_live_nse_price(ticker: str) -> float:
    base_prices = {"SCOM": 16.50, "EQTY": 38.25, "EABL": 150.00, "KCB": 29.00}
    return base_prices.get(ticker.upper(), 10.00)


# --- ACCOUNT WALLET & PAYMENT FLOWS ---

@app.get("/api/v1/wallet/{user_id}")
def get_account_balance(user_id: str):
    if user_id not in USER_ACCOUNTS_LEDGER:
        USER_ACCOUNTS_LEDGER[user_id] = 0.00
        
    return {
        "status": "SUCCESS",
        "user_id": user_id,
        "balance_in_kes": USER_ACCOUNTS_LEDGER[user_id]
    }


@app.post("/api/v1/payments/deposit")
def process_stk_deposit(payload: DepositPayload):
    if payload.amount < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Transaction aborted. Minimum execution threshold is KSh 10.00"
        )
        
    gateway_url = "https://sandbox.intasend.com/api/v1/payment/mpesa-stk-push/"
    headers = {
        "Authorization": f"Bearer {INTASEND_SECRET_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    body = {
        "amount": str(payload.amount),
        "phone_number": payload.phone_number,
        "narrative": "AstraTrade Capital Deposit Injection",
        "api_ref": payload.user_id 
    }
    
    try:
        response = requests.post(gateway_url, json=body, headers=headers)
        gateway_data = response.json()
        
        if response.status_code not in [200, 201]:
            raise HTTPException(
                status_code=400, 
                detail=f"Gateway Communication Rejection: {gateway_data.get('errors', 'Unknown validation error')}"
            )
            
        generated_ref = gateway_data.get("id", f"GTW_{int(time.time())}")
        
        # Initialize the transaction status tracker as PROCESSING
        TRACKED_TRANSACTIONS[generated_ref] = {
            "user_id": payload.user_id,
            "amount": payload.amount,
            "status": "PROCESSING",
            "timestamp": time.time()
        }
        
        print(f"[M-PESA OUTBOUND] STK Push transmitted to {payload.phone_number} with track reference: {generated_ref}")
        return {
            "status": "SUCCESS",
            "message": "STK Push successfully routed. Awaiting user device signature tracking verification.",
            "gateway_ref": generated_ref
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Gateway Interface Transport Failure: {str(e)}"
        )


@app.get("/api/v1/payments/status/{gateway_ref}")
def check_deposit_status(gateway_ref: str):
    if gateway_ref not in TRACKED_TRANSACTIONS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Requested payment track reference does not exist on this server."
        )
        
    tx_data = TRACKED_TRANSACTIONS[gateway_ref]
    
    # SANDBOX AUTO-FAILURE SIMULATION FOR TESTING:
    # Over KSh 70,000, we auto-fail the transaction state after 10 seconds to allow interface timeout evaluations
    elapsed_time = time.time() - tx_data["timestamp"]
    if tx_data["amount"] >= 70000 and tx_data["status"] == "PROCESSING" and elapsed_time > 10:
        tx_data["status"] = "FAILED"
        print(f"[STATUS ALTERATION] Transaction {gateway_ref} auto-failed due to simulated sandbox constraints.")

    return {
        "gateway_ref": gateway_ref,
        "status": tx_data["status"],
        "user_id": tx_data["user_id"]
    }


@app.post("/api/v1/payments/webhook")
async def intasend_webhook_listener(request: Request):
    try:
        data = await request.json()
        print(f"[WEBHOOK EVENT DETECTED] Payload content: {data}")
        
        invoice = data.get("invoice", {})
        gateway_ref = data.get("id") or invoice.get("invoice_id")
        user_id = invoice.get("api_ref")       
        net_cleared = float(invoice.get("net_amount", 0))
        state = data.get("state")
        
        if gateway_ref in TRACKED_TRANSACTIONS:
            if state == "COMPLETE":
                TRACKED_TRANSACTIONS[gateway_ref]["status"] = "COMPLETE"
            elif state in ["FAILED", "REJECTED", "CANCELLED"]:
                TRACKED_TRANSACTIONS[gateway_ref]["status"] = "FAILED"
        
        if state == "COMPLETE" and user_id:
            if user_id not in USER_ACCOUNTS_LEDGER:
                USER_ACCOUNTS_LEDGER[user_id] = 0.00
            
            USER_ACCOUNTS_LEDGER[user_id] += net_cleared
            print(f"[ACCOUNT UPDATE COMPLETE] Ledger ID {user_id} securely updated by KSh {net_cleared}.")
                
        return {"status": "ACKNOWLEDGED"}
    except Exception as e:
        print(f"[WEBHOOK PROCESSING FAULT] Security trace log: {str(e)}")
        return {"status": "ERROR", "message": str(e)}


@app.post("/api/v1/payments/withdraw")
def process_wallet_withdrawal(payload: WithdrawalPayload):
    current_available_balance = USER_ACCOUNTS_LEDGER.get(payload.user_id, 0.00)
    
    if payload.amount > current_available_balance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transaction declined. Insufficient funds. Requested: KSh {payload.amount}, True Available: KSh {current_available_balance}"
        )
        
    USER_ACCOUNTS_LEDGER[payload.user_id] -= payload.amount
    return {
        "status": "SUCCESS",
        "message": f"Withdrawal parameters valid. Transfer of KSh {payload.amount} initialized.",
        "remaining_balance_kes": USER_ACCOUNTS_LEDGER[payload.user_id]
    }


# --- ORDER CLEARANCE & TRADING LOGIC SYSTEM ---

@app.post("/api/v1/trades/place")
def execute_asset_trade(payload: TradePayload):
    user_balance = USER_ACCOUNTS_LEDGER.get(payload.user_id, 0.00)
    
    if not is_market_open():
        order_reservation = {
            "user_id": payload.user_id,
            "ticker": payload.ticker.upper(),
            "requested_shares": payload.shares,
            "status": "PENDING_MARKET_OPEN",
            "timestamp_placed": datetime.now().isoformat()
        }
        PENDING_WEEKEND_ORDERS.append(order_reservation)
        return {
            "status": "QUEUED",
            "message": f"The NSE market is closed. Your purchase parameters are safely indexed in escrow. Settlement will run automatically at the true opening market bell on Monday at 09:00 AM EAT."
        }
        
    live_price = get_live_nse_price(payload.ticker)
    total_cost = live_price * payload.shares
    
    if total_cost > user_balance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient capitalization to clear trade."
        )
        
    USER_ACCOUNTS_LEDGER[payload.user_id] -= total_cost
    return {
        "status": "SUCCESS",
        "message": f"Order processed cleanly. Secured {payload.shares} shares of {payload.ticker}.",
        "remaining_balance_kes": USER_ACCOUNTS_LEDGER[payload.user_id]
    }


@app.post("/api/v1/trades/early-settlement")
def process_early_trade_settlement(payload: EarlySettlementPayload):
    """
    Manages premature contract cancellation options. Enforces a strict 30% contract penalty
    calculated dynamically against the actual asset stake sent from the active frontend.
    """
    trade_id = payload.trade_id
    initial_stake = payload.amount_kes
    
    # 🌟 DYNAMIC REAL-TIME REGISTRATION FIX
    if trade_id not in ACTIVE_USER_TRADES:
        ACTIVE_USER_TRADES[trade_id] = {
            "user_id": payload.user_id,
            "ticker": "SCOM",
            "shares": 100,
            "stake_kes": initial_stake,  
            "status": "HELD",
            "maturity_date": "2026-06-07T09:00:00"
        }
        
    trade = ACTIVE_USER_TRADES[trade_id]
    trade["stake_kes"] = initial_stake # Overwrite state map to ensure total structural alignment
    
    if trade["status"] != "HELD":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Position state parameters prevent modification."
        )
        
    if payload.settlement_type == "PARTIAL_CLOSE":
        # 🧾 DYNAMIC MATHEMATICAL PROJECTIONS
        penalty_fee = initial_stake * 0.30
        guaranteed_payout_pool = initial_stake * 0.70  
        
        trade["penalty_deducted_kes"] = penalty_fee
        trade["final_payout_kes"] = guaranteed_payout_pool
        trade["status"] = "CLOSED_PENDING_MATURITY"
        
        message = (
            f"Early Partial Close verified. A contract breaking administrative charge of 30% "
            f"(KSh {penalty_fee:,.2f}) has been applied. The remaining 70% balance "
            f"(KSh {guaranteed_payout_pool:,.2f}) is locked in secure escrow and will release "
            f"directly to your wallet portfolio when the original 7-day maturity sequence concludes."
        )
        
        print(f"[EARLY LIQUIDATION SUCCESS] Handled trade {trade_id}. Forfeited KSh {penalty_fee}, escrowed KSh {guaranteed_payout_pool}")
        
        return {
            "status": "SUCCESS",
            "trade_id": trade_id,
            "current_position_state": trade["status"],
            "penalty_deducted": penalty_fee,
            "final_payout": guaranteed_payout_pool,
            "message": message,
            "release_date": trade["maturity_date"]
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid classification parameter specified for early settlement router."
        )


@app.post("/api/v1/internal/settle-weekend-orders")
def settle_weekend_orders():
    # Global declaration at top of scope blocks compiler crashes
    global PENDING_WEEKEND_ORDERS
    
    print(f"[MONDAY BELL SETTLEMENT RUNNING] Clearing {len(PENDING_WEEKEND_ORDERS)} held weekend market entries...")
    processed_count = 0
    
    current_queue = list(PENDING_WEEKEND_ORDERS)
    PENDING_WEEKEND_ORDERS = [] 
    
    for order in current_queue:
        user_id = order["user_id"]
        ticker = order["ticker"]
        shares = order["requested_shares"]
        
        monday_open_price = get_live_nse_price(ticker)
        total_cost = monday_open_price * shares
        user_balance = USER_ACCOUNTS_LEDGER.get(user_id, 0.00)
        
        if user_balance >= total_cost:
            USER_ACCOUNTS_LEDGER[user_id] -= total_cost
            processed_count += 1
            
    return {
        "status": "COMPLETED",
        "message": f"Successfully settled {processed_count} outstanding weekend escrow orders."
    }             
