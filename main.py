import base64
from datetime import datetime
import httpx
import os
from fastapi import FastAPI, BackgroundTasks, Body

app = FastAPI()

# These will be securely loaded from Render's dashboard settings later
CONSUMER_KEY = os.getenv("MPESA_CONSUMER_KEY")
CONSUMER_SECRET = os.getenv("MPESA_CONSUMER_SECRET")
SHORTCODE = "174379"
PASSKEY = "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919"

@app.get("/")
def home():
    return {"status": "AstraTrade Cloud Backend Is Live!"}

@app.post("/deposit")
async def initiate_deposit(data: dict = Body(...)):
    phone = data.get("phone")  # Format: 2547XXXXXXXX
    amount = data.get("amount")
    
    # Render automatically generates a public URL for your app, which we grab dynamically
    app_url = os.getenv("RENDER_EXTERNAL_URL")
    callback_url = f"{app_url}/mpesa-callback"

    # 1. Generate M-Pesa Password
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password = base64.b64encode(f"{SHORTCODE}{PASSKEY}{timestamp}".encode()).decode("utf-8")

    # 2. Fetch Safaricom Token
    auth_url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    async with httpx.AsyncClient() as client:
        token_res = await client.get(auth_url, auth=(CONSUMER_KEY, CONSUMER_SECRET))
        token = token_res.json()["access_token"]

    # 3. Trigger PIN Prompt on User's Phone
    stk_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "BusinessShortCode": SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": amount,
        "PartyA": phone,
        "PartyB": SHORTCODE,
        "PhoneNumber": phone,
        "CallBackURL": callback_url,
        "AccountReference": "AstraTradeWeb",
        "TransactionDesc": "Web Cloud Live Test"
    }
    
    stk_res = await client.post(stk_url, json=payload, headers=headers)
    return stk_res.json()

@app.post("/mpesa-callback")
async def mpesa_callback(payload: dict = Body(...)):
    print("M-PESA PAYMENT SUCCESS DATA:", payload)
    return {"ResultCode": 0, "ResultDesc": "Success"}
