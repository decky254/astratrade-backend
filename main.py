import base64
from datetime import datetime
import httpx
import os
from fastapi import FastAPI, Body

app = FastAPI()

# ==================== PASTE YOUR SAFARICOM KEYS HERE ====================
CONSUMER_KEY = "pk668GMc9GGrZ8VAnZ6VzOAj6vGAUGA6"
CONSUMER_SECRET = "7A0tA6W4f6OAA77G"
# ========================================================================

SHORTCODE = "174379"
PASSKEY = "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919"

@app.get("/")
def home():
    return {"status": "AstraTrade Cloud Backend Is Live!"}

@app.post("/deposit")
async def initiate_deposit(data: dict = Body(...)):
    phone = data.get("phone")  # Expected format: 2547XXXXXXXX
    amount = data.get("amount")
    
    # Dynamically grab your Render URL path
    app_url = os.getenv("RENDER_EXTERNAL_URL", "https://astratrade-backend-9fk0.onrender.com")
    callback_url = f"{app_url}/mpesa-callback"

    # 1. Create the security password timestamp
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password_data = f"{SHORTCODE}{PASSKEY}{timestamp}"
    password = base64.b64encode(password_data.encode()).decode("utf-8")

    # 2. Fetch OAuth Token with explicitly caught response details
    auth_url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    async with httpx.AsyncClient() as client:
        try:
            token_res = await client.get(auth_url, auth=(CONSUMER_KEY, CONSUMER_SECRET))
            
            # If Safaricom sends any structural rejection, echo it directly to ReqBin
            if token_res.status_code != 200:
                return {
                    "error": "Safaricom rejected your Consumer Credentials",
                    "http_status": token_res.status_code,
                    "safaricom_raw_error": token_res.text
                }
                
            token = token_res.json()["access_token"]
        except Exception as err:
            return {
                "error": "Failed to connect to Safaricom network",
                "exception_details": str(err)
            }

    # 3. Request the STK Push prompt layout
    stk_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "BusinessShortCode": SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": phone,
        "PartyB": SHORTCODE,
        "PhoneNumber": phone,
        "CallBackURL": callback_url,
        "AccountReference": "AstraTradeWeb",
        "TransactionDesc": "Web Cloud Direct Test"
    }
    
    stk_res = await client.post(stk_url, json=payload, headers=headers)
    return stk_res.json()

@app.post("/mpesa-callback")
async def mpesa_callback(payload: dict = Body(...)):
    print("M-PESA TRANSACTION LOG RECEIVED:", payload)
    return {"ResultCode": 0, "ResultDesc": "Success"}
