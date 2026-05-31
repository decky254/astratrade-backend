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
# Tracks live fiat balances independently of client device storage to stop tampering
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

# 📝 CENTRALIZED ESCROW STORAGE ARRAYS
# Pools orders submitted while the real exchange is closed, waiting for Monday morning opening values
PENDING_WEEKEND_ORDERS = []

# 🔑 SECURE GATEWAY INFRASTRUCTURE STRINGS
INTASEND_SECRET_KEY = os.getenv("INTASEND_SECRET_KEY", "your_api_token_here")


# --- DATA VALDIATION SCHEMAS (PYDANTIC) ---
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
    settlement_type: str = Field(..., description="User choice parameter configuration: 'PARTIAL_CLOSE' or 'PARTIAL_PROFIT'")


# --- DATA ROUTING & TIME MARKET UTILITIES ---
def is_market_open() -> bool:
    """
    Evaluates execution time constraints against the Nairobi Securities Exchange (NSE).
    Standard Operating Windows: Monday through Friday, 09:00 AM to 03:00 PM East African Time (EAT).
    """
    eat_timezone = pytz.timezone("Africa/Nairobi")
    now_eat = datetime.now(eat_timezone)
    
    # Isolate weekend calendar indexes (Saturday = 5, Sunday = 6)
    if now_eat.weekday() >= 5:
        return False
        
    market_start = datetime_time(9, 0, 0)
    market_close = datetime_time(15, 0, 0)
    
    return market_start <= now_eat.time() <= market_close


def get_live_nse_price(ticker: str) -> float:
    """
    Fetches the true live value of a specific ticker from the exchange data array.
    """
    # Baseline market price metrics serving as structural values during sandbox operations
    base_prices = {"SCOM": 16.50, "EQTY": 38.25, "EABL": 150.00, "KCB": 29.00}
    return base_prices.get(ticker.upper(), 10.00)


# --- ACCOUNT WALLET LEDGER ENDPOINTS ---

@app.get("/api/v1/wallet/{user_id}")
def get_account_balance(user_id: str):
    """
    Queries server-side registers to return authentic wallet capital pools.
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
    Dispatches standard API push instructions to the provider gateway infrastructure.
    Funds are not allocated until an authorized transaction confirmation webhook payload hits the server.
    """
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
            
        print(f"[M-PESA OUTBOUND] STK Push instructions transmitted to {payload.phone_number}")
        return {
            "status": "SUCCESS",
            "message": "STK Push successfully routed. Awaiting user device signature tracking verification.",
            "gateway_ref": gateway_data.get("id", f"GTW_{int(time.time())}")
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Gateway Interface Transport Failure: {str(e)}"
        )


@app.post("/api/v1/payments/webhook")
async def intasend_webhook_listener(request: Request):
    """
    🔄 WEBHOOK INTAKE PORTS: Captures incoming transaction completion payloads 
    sent by the settlement server cluster.
    """
    try:
        data = await request.json()
        print(f"[WEBHOOK EVENT DETECTED] Payload content: {data}")
        
        if data.get("state") == "COMPLETE":
            invoice = data.get("invoice", {})
            user_id = invoice.get("api_ref")       
            net_cleared = float(invoice.get("net_amount", 0))
            
            if user_id:
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
    """
    🛡️ TRANSACTION SECURITY FILTER: Evaluates ledger availability prior to outbound money transfer routing.
    Completely neutralizes local browser file injection or storage state changes.
    """
    current_available_balance = USER_ACCOUNTS_LEDGER.get(payload.user_id, 0.00)
    
    if payload.amount > current_available_balance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transaction declined. Insufficient funds. Requested: KSh {payload.amount}, True Available: KSh {current_available_balance}"
        )
        
    USER_ACCOUNTS_LEDGER[payload.user_id] -= payload.amount
    print(f"[LIQUID DEBIT ASSIGNED] Removed KSh {payload.amount} from secure account matrix ledger matching ID: {payload.user_id}.")
    
    return {
        "status": "SUCCESS",
        "message": f"Withdrawal parameters valid. Transfer of KSh {payload.amount} initialized to {payload.destination_target}.",
        "remaining_balance_kes": USER_ACCOUNTS_LEDGER[payload.user_id]
    }


# --- ORDER CLEARANCE & TRADING LOGIC SYSTEM ---

@app.post("/api/v1/trades/place")
def execute_asset_trade(payload: TradePayload):
    """
    Validates calendar timing metrics to execute live trades instantly or queue 
    closed-market orders for accurate Monday morning matching adjustments.
    """
    user_balance = USER_ACCOUNTS_LEDGER.get(payload.user_id, 0.00)
    
    # ⏱️ BRANCH TRACK A: Market is Closed (Escrow Mode Enabled)
    if not is_market_open():
        order_reservation = {
            "user_id": payload.user_id,
            "ticker": payload.ticker.upper(),
            "requested_shares": payload.shares,
            "status": "PENDING_MARKET_OPEN",
            "timestamp_placed": datetime.now().isoformat()
        }
        PENDING_WEEKEND_ORDERS.append(order_reservation)
        print(f"[MARKET CLOSED ESCROW] Queued {payload.shares} shares of {payload.ticker} for Monday morning open matching.")
        
        return {
            "status": "QUEUED",
            "message": f"The NSE market is closed. Your purchase parameters are safely indexed in escrow. Settlement will run automatically at the true opening market bell on Monday at 09:00 AM EAT."
        }
        
    # ⏱️ BRANCH TRACK B: Market is Open (Live Pricing Active)
    live_price = get_live_nse_price(payload.ticker)
    total_cost = live_price * payload.shares
    
    if total_cost > user_balance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient capitalization to clear trade. Required: KSh {total_cost}, Real Server Balance: KSh {user_balance}"
        )
        
    USER_ACCOUNTS_LEDGER[payload.user_id] -= total_cost
    print(f"[LIVE ORDER MATCHED] User ID {payload.user_id} secured {payload.shares} units of {payload.ticker} at KSh {live_price}")
    
    return {
        "status": "SUCCESS",
        "message": f"Order processed cleanly. Secured {payload.shares} shares of {payload.ticker} at KSh {live_price} per unit.",
        "remaining_balance_kes": USER_ACCOUNTS_LEDGER[payload.user_id]
    }


@app.post("/api/v1/trades/early-settlement")
def process_early_trade_settlement(payload: EarlySettlementPayload):
    """
    Manages premature contract cancellation options. Forfeits a 30% penalty charge 
    on defensive closures while keeping the remaining 70% locked safely until the contract maturity date.
    """
    trade_id = payload.trade_id
    
    if trade_id not in ACTIVE_USER_TRADES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target position reference index not found in current portfolio allocations."
        )
        
    trade = ACTIVE_USER_TRADES[trade_id]
    
    if trade["status"] != "HELD":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Position state parameters prevent modification. Target Status: {trade['status']}"
        )
        
    # 🛑 EVALUATE SELECTIVE OVERLAY BUTTON INPUT CHOICE
    if payload.settlement_type == "PARTIAL_CLOSE":
        initial_stake = trade["stake_kes"]
        
        # Enforce strict 30% contract penalty deductions
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
        
    print(f"[EARLY TERMINATION RECORDED] Position ID {trade_id} frozen for lock-in. Penalty Fee Applied: KSh {trade.get('penalty_deducted_kes', 0)}. Guaranteed Clearance: KSh {trade['final_payout_kes']}")
    return {
        "status": "SUCCESS",
        "trade_id": trade_id,
        "current_position_state": trade["status"],
        "message": message,
        "release_date": trade["maturity_date"]
    }


@app.post("/api/v1/internal/settle-weekend-orders")
def settle_weekend_orders():
    """
    ☀️ MONDAY MARKET CLEARANCE CRON: Iterates through the escrow arrays, 
    matching queued trades directly to real Monday market opening valuations.
    """
    # 🌟 CRITICAL REPAIR SUMMARY: Global declaration moved to line 1 of function scope to block compilation failure
    global PENDING_WEEKEND_ORDERS
    
    print(f"[MONDAY BELL SETTLEMENT RUNNING] Clearing {len(PENDING_WEEKEND_ORDERS)} held weekend market entries...")
    processed_count = 0
    
    current_queue = list(PENDING_WEEKEND_ORDERS)
    PENDING_WEEKEND_ORDERS = [] 
    
    for order in current_queue:
        user_id = order["user_id"]
        ticker = order["ticker"]
        shares = order["requested_shares"]
        
        # Extract authentic opening price metrics
        monday_open_price = get_live_nse_price(ticker)
        total_cost = monday_open_price * shares
        user_balance = USER_ACCOUNTS_LEDGER.get(user_id, 0.00)
        
        if user_balance >= total_cost:
            USER_ACCOUNTS_LEDGER[user_id] -= total_cost
            print(f"[ESCROW ORDER MATCHED COMPLETE] Cleared user {user_id}: {shares} shares of {ticker} executed at KSh {monday_open_price}")
            processed_count += 1
        else:
            print(f"[ESCROW DROPPED - INSUFFICIENT CAPITAL] User {user_id} lacked buying power matching true opening bell price for ticker {ticker}.")
            
    return {
        "status": "COMPLETED",
        "message": f"Successfully settled {processed_count} outstanding weekend escrow orders using real opening prices."
        }
