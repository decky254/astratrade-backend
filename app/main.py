import os
import time
import random
import requests
from datetime import datetime, time as datetime_time
import pytz
from fastapi import FastAPI, HTTPException, status, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(
    title="AstraTrade Institutional Financial & Market Engine",
    description="Unified API hosting secure M-Pesa ledger tracks, automated NSE market settlement routines, early position liquidation protocols, and synthetic binary forecasting."
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
ACTIVE_USER_TRADES = {
    "trade_sample_001": {
        "user_id": "user_test_id",
        "ticker": "SCOM",
        "shares": 100,
        "stake_kes": 1650.00,
        "status": "HELD",
        "maturity_date": "2026-06-07T09:00:00"
    }
}

# Real-time state registers for the new Synthetic Binary Contracts
BINARY_OPTIONS_LEDGER = {}

# Audit trail tracking for Terms of Service (ToS) agreements
TERMS_AGREEMENTS_LOG = {}

# Tracks the real-time status of pushed transactions to catch failures (e.g., Insufficient Funds)
TRACKED_TRANSACTIONS = {}

# 📝 CENTRALIZED ESCROW STORAGE ARRAYS
PENDING_WEEKEND_ORDERS = []

# 🔑 SECURE GATEWAY INFRASTRUCTURE STRINGS
# If using Live Production later, simply swap the Environment Variable to your Live Secret Token
INTASEND_SECRET_KEY = os.getenv("INTASEND_SECRET_KEY", "your_api_token_here")


# --- DATA VALIDATION SCHEMAS (PYDANTIC) ---

class RegisterPayload(BaseModel):
    username: str

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

class BinaryTradePayload(BaseModel):
    user_id: str
    symbol: str = Field(..., description="Local company option asset code (e.g., SCOM, EQTY, EABL)")
    stake: float = Field(..., description="Wager amount placed on the contract outcome", gt=0)
    direction: str = Field(..., description="Market predictive constraint vector: 'CALL' or 'PUT'")

class EarlySettlementPayload(BaseModel):
    user_id: str
    trade_id: str
    settlement_type: str = Field(..., description="User choice parameter configuration: 'PARTIAL_CLOSE' or 'PARTIAL_PROFIT'")


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


# --- ACCOUNT AUDIT & SECURITY COMPLIANCE ---

@app.post("/api/v1/auth/register")
def register_and_accept_terms(payload: RegisterPayload, request: Request):
    """
    Implements mandatory audit logging mapping directly to your frontend click-wrap interface.
    Saves user consent alongside metadata to protect system records.
    """
    generated_user_id = f"usr_{int(time.time())}"
    
    # Instantiate user profile balance sheet entry
    USER_ACCOUNTS_LEDGER[generated_user_id] = 0.00
    
    # Audit log capture
    client_ip = request.client.host if request.client else "unknown"
    TERMS_AGREEMENTS_LOG[generated_user_id] = {
        "agreed_at": datetime.utcnow().isoformat(),
        "terms_version": "v1.0",
        "ip_address": client_ip
    }
    
    print(f"[SECURITY AUDIT LOG] User {generated_user_id} registered and signed ToS v1.0 from IP {client_ip}")
    return {
        "status": "SUCCESS",
        "user_id": generated_user_id,
        "message": "User file initialized. Mandatory Terms of Service consent recorded successfully."
    }


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
        
        # Initialize transaction tracer as PROCESSING
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
        
        # Sync to our local tracking ledger map
        if gateway_ref in TRACKED_TRANSACTIONS:
            if state == "COMPLETE":
                TRACKED_TRANSACTIONS[gateway_ref]["status"] = "COMPLETE"
            elif state in ["FAILED", "REJECTED", "CANCELLED"]:
                TRACKED_TRANSACTIONS[gateway_ref]["status"] = "FAILED"
        
        # Credit wallet if payment cleared successfully
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


# --- ORDER CLEARANCE & STANDARD TRADING ROUTINES ---

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
            "message": "The NSE market is closed. Settlement will run automatically at the true opening market bell on Monday at 09:00 AM EAT."
        }
        
    live_price = get_live_nse_price(payload.ticker)
    total_cost = live_price * payload.shares
    
    if total_cost > user_balance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insufficient capitalization to clear trade."
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
    Manages premature contract cancellation options. Forfeits a 30% penalty charge 
    on defensive closures while keeping the remaining 70% locked safely until maturity.
    """
    trade_id = payload.trade_id
    
    if trade_id not in ACTIVE_USER_TRADES:
        ACTIVE_USER_TRADES[trade_id] = {
            "user_id": payload.user_id,
            "ticker": "SCOM",
            "shares": 100,
            "stake_kes": 25000.00,  
            "status": "HELD",
            "maturity_date": "2026-06-07T09:00:00"
        }
        
    trade = ACTIVE_USER_TRADES[trade_id]
    
    if trade["status"] != "HELD":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Position state parameters prevent modification."
        )
        
    if payload.settlement_type == "PARTIAL_CLOSE":
        initial_stake = trade["stake_kes"]
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
        
    elif payload.settlement_type == "PARTIAL_PROFIT":
        trade["final_payout_kes"] = trade["stake_kes"] + 150.00 
        trade["status"] = "CLOSED_PENDING_MATURITY"
        message = "Partial profit taking configuration active. Accrued gains locked and frozen; transfer runs at maturity date."
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid classification parameter specified for early settlement router."
        )
        
    return {
        "status": "SUCCESS",
        "trade_id": trade_id,
        "current_position_state": trade["status"],
        "message": message,
        "release_date": trade["maturity_date"]
    }


@app.post("/api/v1/internal/settle-weekend-orders")
def settle_weekend_orders():
    global PENDING_WEEKEND_ORDERS
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


# --- SYNTHETIC BINARY ENGINE (20% WIN RATE & HOUSING PROTECTION CONTROLS) ---

@app.post("/api/v1/trades/binary")
def place_synthetic_binary_option(payload: BinaryTradePayload):
    """
    Places a time-bound binary prediction options contract for local equities.
    Deducts the stake, tracks the multiplier, and checks house liability limits.
    """
    user_balance = USER_ACCOUNTS_LEDGER.get(payload.user_id, 0.00)
    if payload.stake > user_balance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Trade declined. Insufficient ledger funds. Balance: KSh {user_balance:,.2f}"
        )
        
    # House Rules Configuration
    payout_multiplier = 3.2  # Calibrated configuration for the desired 20% win edge
    raw_potential_payout = payload.stake * payout_multiplier
    house_exposure_limit = 5000.00  # Hard protection ceiling
    
    # Enforce House Liability Shielding Cap
    is_capped = False
    final_allowable_payout = raw_potential_payout
    if raw_potential_payout > house_exposure_limit:
        final_allowable_payout = house_exposure_limit
        is_capped = True
        
    # Deduct structural risk asset stake from account balance
    USER_ACCOUNTS_LEDGER[payload.user_id] -= payload.stake
    
    # Store binary tracking block
    binary_trade_id = f"bin_{int(time.time())}_{random.randint(100,999)}"
    BINARY_OPTIONS_LEDGER[binary_trade_id] = {
        "user_id": payload.user_id,
        "symbol": payload.symbol.upper(),
        "stake_amount": payload.stake,
        "direction": payload.direction.upper(),
        "payout_multiplier": payout_multiplier,
        "potential_payout": final_allowable_payout,
        "is_capped": is_capped,
        "status": "OPEN",
        "created_at": datetime.utcnow().isoformat()
    }
    
    print(f"[BINARY ESCROW REGISTERED] Option {binary_trade_id} locked. Cap Active: {is_capped}")
    return {
        "status": "SUCCESS",
        "trade_id": binary_trade_id,
        "potential_payout": final_allowable_payout,
        "is_payout_capped": is_capped,
        "message": "Binary contract active. Positions are resolved upon portfolio dashboard synchronization."
    }


@app.get("/api/v1/trades/binary/history/{user_id}")
def get_binary_options_history(user_id: str):
    """
    Runs an on-demand background settlement loop over open trades before rendering 
    the list items to your frontend profile screen.
    Ensures mathematical house edge (20% win probability) is fully maintained.
    """
    user_records = []
    
    for trade_id, trade_data in BINARY_OPTIONS_LEDGER.items():
        if trade_data["user_id"] == user_id:
            # If the trade is still 'OPEN', resolve it instantly via the weighted probability algorithm
            if trade_data["status"] == "OPEN":
                # Mathematical Edge: User wins if random draw falls inside a strict 20% bracket
                probability_draw = random.random()
                
                if probability_draw <= 0.20:
                    trade_data["status"] = "WON"
                    # Credit winning payout to the system wallet ledger
                    USER_ACCOUNTS_LEDGER[user_id] += trade_data["potential_payout"]
                    print(f"[ENGINE SETTLED - WIN] Contract {trade_id} won. Credited KSh {trade_data['potential_payout']}.")
                else:
                    trade_data["status"] = "LOST"
                    print(f"[ENGINE SETTLED - LOSS] Contract {trade_id} lost. House retains KSh {trade_data['stake_amount']}.")
            
            # Formulate the payload object array item
            user_records.append({
                "trade_id": trade_id,
                "symbol": trade_data["symbol"],
                "stake": trade_data["stake_amount"],
                "direction": trade_data["direction"],
                "payout": trade_data["potential_payout"],
                "is_capped": trade_data["is_capped"],
                "status": trade_data["status"],
                "created_at": trade_data["created_at"]
            })
            
    return {
        "status": "SUCCESS",
        "user_id": user_id,
        "history": user_records
}
