import base64
from datetime import datetime
import httpx
import os
from fastapi import FastAPI, Body

app = FastAPI()

# ==================== PASTE YOUR SAFARICOM KEYS HERE ====================
CONSUMER_KEY = "PASTE_YOUR_ACTUAL_DARAJA_CONSUMER_KEY_HERE"
CONSUMER_SECRET = "PASTE_YOUR_ACTUAL_DARAJA_CONSUMER_SECRET_HERE"
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
    
    # Render provides your unique website URL dynamically via this system string
    app_url = os.getenv("RENDER_EXTERNAL_URL", "https://astratrade-backend-9fk0.onrender.com")
    callback_url = f"{app_url}/mpesa-callback"

    # 1. Create the timestamped Security Password for Safaricom
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password_data = f"{SHORTCODE}{PASSKEY}{timestamp}"
    password = base64.b64encode(password_data.encode()).decode("utf-8")

    # 2. Fetch the Live OAuth Access Token from Daraja
    auth_url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    async with httpx.AsyncClient() as client:
        token_res = await client.get(auth_url, auth=(CONSUMER_KEY, CONSUMER_SECRET))
        
        # If Safaricom rejects your keys, this will print the exact reason in Render Logs
        if token_res.status_code != 200:
            return {
                "error": "Safaricom rejected your Consumer Credentials",
                "safaricom_response": token_res.text
            }
            
        token = token_res.json()["access_token"]

    # 3. Fire the STK Push prompt to your phone
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
    # Safaricom hits this endpoint automatically when you type your PIN
    print("M-PESA TRANSACTION LOG RECEIVED:", payload)
    return {"ResultCode": 0, "ResultDesc": "Success"} 
