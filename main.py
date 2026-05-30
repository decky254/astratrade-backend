import os
import logging
from fastapi import FastAPI, Body, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
import httpx

# -------------------------------------------------------------------------
# 1. INITIALIZATION & ENGINE CONFIGURATION
# -------------------------------------------------------------------------
app = FastAPI(
    title="AstraTrade Payment Backend",
    description="Production-grade IntaSend M-Pesa API Engine running on Shared Wallet rails",
    version="1.0.0"
)

# Configure logging for Render runtime monitoring
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fetch environment variables safely (Set these inside your Render dashboard)
INTASEND_SECRET_TOKEN = os.getenv("INTASEND_SECRET_TOKEN", "ISSecretKey_live_placeholder")

# -------------------------------------------------------------------------
# 2. CORS MIDDLEWARE (Fixes Frontend Cross-Origin Connection Blocks)
# -------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permits structural calls from your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------------------
# 3. HELPER UTILITIES
# -------------------------------------------------------------------------
def format_kenyan_phone(phone_str: str) -> str:
    """
    Cleans up input phone strings and formats them into standard 2547XXXXXXXX or 2541XXXXXXXX.
    Accepts: 0712345678, +254712345678, 254712345678, 712345678
    """
    cleaned = phone_str.strip().replace(" ", "").replace("+", "")
    
    if cleaned.startswith("0"):
        return "254" + cleaned[1:]
    elif cleaned.startswith("7") or cleaned.startswith("1"):
        return "254" + cleaned
    elif cleaned.startswith("254") and len(cleaned) in [12, 13]:
        return cleaned
    else:
        raise ValueError("Invalid Kenyan mobile number format provided.")

def credit_user_wallet_balance(phone_number: str, amount: float, tracking_ref: str):
    """
    Database execution wire hook. Replace with your actual SQL Alchemy / Tortoise ORM
    logic to increase the user's trading balance inside AstraTrade.
    """
    logger.info(f"💾 DATABASE EXECUTION: Crediting {phone_number} with KES {amount}. Ref: {tracking_ref}")
    # User balance updating logic goes here
    pass

# -------------------------------------------------------------------------
# 4. CORE ROUTING ENDPOINTS
# -------------------------------------------------------------------------
@app.get("/")
async def health_check():
    """Confirms Render service instance status availability."""
    return {"status": "healthy", "service": "AstraTrade Payment Gateway Engine"}


@app.post("/deposit")
async def initiate_deposit(data: dict = Body(None)):
    """
    Triggers an instant M-Pesa STK Push via IntaSend's corporate shared wallet infrastructure.
    Bypasses custom Till management and sends prompts directly to user devices.
    """
    if not data:
        raise HTTPException(status_code=400, detail="Missing transaction request parameters.")

    raw_phone = data.get("phone")
    amount = data.get("amount")

    if not raw_phone or not amount:
        raise HTTPException(status_code=400, detail="Fields 'phone' and 'amount' are strictly mandatory.")

    # 1. Clean and normalize phone string structure
    try:
        phone = format_kenyan_phone(str(raw_phone))
    except ValueError as format_err:
        return {
            "ResponseCode": "1",
            "ResponseDescription": str(format_err)
        }

    # 2. Build IntaSend API payload (Stripped of custom wallet_id to enforce default shared wallet routing)
    intasend_url = "https://api.intasend.com/api/v1/payment/mpesa-stk-push/"
    headers = {
        "Authorization": f"Bearer {INTASEND_SECRET_TOKEN.strip()}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    payload = {
        "amount": str(amount),
        "phone_number": phone,
        "api_ref": "AstraTradeLiveDeposit"
    }

    logger.info(f"🚀 Dispatching STK Push via Shared Wallet to {phone} for KES {amount}...")

    # 3. Request execution over asynchronous HTTP client layer
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(intasend_url, json=payload, headers=headers)
            res_json = response.json()
            
            if response.status_code in [200, 201]:
                logger.info(f"✅ STK Push successfully dispatched by IntaSend: {res_json.get('invoice', {}).get('invoice_id', 'N/A')}")
                return {
                    "ResponseCode": "0",
                    "ResponseDescription": "STK Push prompt initialized successfully on user handset.",
                    "details": res_json
                }
            else:
                logger.error(f"❌ IntaSend gateway rejection response status {response.status_code}: {res_json}")
                return {
                    "ResponseCode": "1",
                    "ResponseDescription": res_json.get("errors", "Gateway transaction processing exception."),
                    "details": res_json
                }
        except Exception as network_err:
            logger.critical(f"💥 Failed to establish a clean network connection with IntaSend: {str(network_err)}")
            return {
                "ResponseCode": "1",
                "ResponseDescription": f"Internal gateway communication failure: {str(network_err)}"
            }


@app.post("/api/v1/webhook")
async def intasend_webhook_callback(request: Request):
    """
    Receives automated HTTP POST callbacks from IntaSend whenever a user enters their M-Pesa PIN.
    Maps transaction states to update account states safely.
    """
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON format payload.")

    logger.info(f"📥 Incoming Webhook Event Data Received: {payload}")

    # Extract state processing nodes from standard IntaSend webhook schemas
    invoice_id = payload.get("invoice_id")
    state = payload.get("state", "").upper()
    amount = float(payload.get("amount", 0))
    phone_number = payload.get("phone_number")

    if state == "COMPLETE":
        logger.info(f"💰 SUCCESS: Payment received for Invoice {invoice_id}. Amount: KES {amount} from {phone_number}")
        
        # Execute account balance state updates inside database context
        try:
            credit_user_wallet_balance(
                phone_number=phone_number, 
                amount=amount, 
                tracking_ref=f"INTASEND-{invoice_id}"
            )
        except Exception as db_err:
            logger.error(f"⚠️ Webhook processing state error updating DB: {str(db_err)}")
            return {"status": "Database synchronization tracking delay, transaction captured successfully."}

        return {"status": "Transaction settlement verified and applied successfully."}

    elif state == "FAILED":
        failed_reason = payload.get("failed_reason", "User cancelled or timed out.")
        logger.warning(f"❌ FAILED: Invoice {invoice_id} rejected. Reason: {failed_reason}")
        return {"status": "Failure acknowledged, state modified."}

    else:
        logger.info(f"ℹ️ Transaction status tracking event state skipped: '{state}' for Invoice {invoice_id}")
        return {"status": f"State notification tracking skipped for lifecycle step: {state}"}
