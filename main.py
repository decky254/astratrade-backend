import os
import httpx
from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# ==================== CORS SECURITY MIDDLEWARE ====================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows your Google Cloud Run frontend to connect cleanly
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== INTASEND SECURITY KEYS ====================
INTASEND_SECRET_TOKEN = "ISSecretKey_live_96a1d59e-e4d9-4dbe-b57b-584f0d1c1fb3"
# ================================================================

@app.get("/")
def home():
    return {"status": "AstraTrade Backend Connected to IntaSend Deposit & Withdrawal Engines!"}


# ==================== DEPOSIT ENDPOINT (STK PUSH) ====================
@app.post("/deposit")
async def initiate_deposit(data: dict = Body(None)):
    if not data:
        return {"error": "Payload is empty"}

    raw_phone = data.get("phone", "")
    amount = data.get("amount", 10)

    phone = raw_phone.strip()
    if phone.startswith("0"):
        phone = "254" + phone[1:]
    elif phone.startswith("+"):
        phone = phone.replace("+", "")

    intasend_url = "https://api.intasend.com/api/v1/payment/mpesa-stk-push/"
    headers = {
        "Authorization": f"Bearer {INTASEND_SECRET_TOKEN.strip()}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    payload = {
        "amount": str(amount),
        "phone_number": phone,
        "api_ref": "AstraTradeWebDeposit"
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(intasend_url, json=payload, headers=headers)
            res_json = response.json()
            if response.status_code in [200, 201]:
                return {"ResponseCode": "0", "ResponseDescription": "Success", "details": res_json}
            return {"ResponseCode": "1", "ResponseDescription": res_json.get("errors", "Failed"), "details": res_json}
        except Exception as err:
            return {"ResponseCode": "1", "ResponseDescription": str(err)}


# ==================== WITHDRAWAL ENDPOINT (B2C PAYOUT) ====================
@app.post("/withdraw")
async def initiate_withdrawal(data: dict = Body(None)):
    if not data:
        return {"error": "Payload is empty"}

    raw_phone = data.get("phone", "")
    amount = data.get("amount", 10)
    customer_name = data.get("name", "AstraTrade User") # IntaSend requires a name for reference

    phone = raw_phone.strip()
    if phone.startswith("0"):
        phone = "254" + phone[1:]
    elif phone.startswith("+"):
        phone = phone.replace("+", "")

    # IntaSend Payout (Send Money) Destination URL
    payout_url = "https://api.intasend.com/api/v1/send-money/mpesa/"
    
    headers = {
        "Authorization": f"Bearer {INTASEND_SECRET_TOKEN.strip()}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    # IntaSend expects transactions structured in a list format (supports bulk, but we pass one)
    payload = {
        "currency": "KES",
        "requires_approval": "NO", # "NO" releases the money to their phone instantly without manual dashboard approval
        "transactions": [
            {
                "name": customer_name,
                "account": phone,
                "amount": str(amount),
                "narrative": "AstraTrade Balance Withdrawal"
            }
        ]
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(payout_url, json=payload, headers=headers)
            res_json = response.json()
            
            if response.status_code in [200, 201]:
                return {
                    "ResponseCode": "0",
                    "ResponseDescription": "Withdrawal processed successfully!",
                    "details": res_json
                }
            return {
                "ResponseCode": "1",
                "ResponseDescription": res_json.get("errors", "Withdrawal processing rejected"),
                "details": res_json
            }
        except Exception as err:
            return {"ResponseCode": "1", "ResponseDescription": str(err)}
