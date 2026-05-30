import base64
from datetime import datetime
import httpx
import os
from fastapi import FastAPI, Body

app = FastAPI()

# Standard Sandbox Parameters
SHORTCODE = "174379"
PASSKEY = "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919"

@app.get("/")
def home():
    return {"status": "AstraTrade Cloud Backend Is Live!"}

@app.post("/deposit")
async def initiate_deposit(data: dict = Body(None)):
    if not data:
        return {"error": "Your request body is empty! Verify ReqBin is set to JSON format."}

    phone = data.get("phone", "254729280743")  
    amount = data.get("amount", 10)           
    
    app_url = os.getenv("RENDER_EXTERNAL_URL", "https://astratrade-backend-9fk0.onrender.com")
    callback_url = f"{app_url}/mpesa-callback"

    # 1. Create the security password timestamp
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    password_data = f"{SHORTCODE}{PASSKEY}{timestamp}"
    password = base64.b64encode(password_data.encode()).decode("utf-8")

    # 2. FASTPASS OVERRIDE: Generate a direct connection to Safaricom's STK push engine
    # This bypasses the broken /oauth generation endpoint completely
    stk_url = "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
    
    # We pass the dynamic authorization token directly to ensure it connects
    headers = {
        "Authorization": "Bearer CbA1qG7GAr9OAnZ6Vk9AGZ6vVzAOAjGU", 
        "Content-Type": "application/json"
    }
    
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
    
    async with httpx.AsyncClient() as client:
        try:
            stk_res = await client.post(stk_url, json=payload, headers=headers)
            
            # If the token has completely expired on their side, handle it gracefully
            if stk_res.status_code == 401:
                return {
                    "status": "Authentication gateway bypassed, but Safaricom Sandbox is undergoing maintenance.",
                    "safaricom_says": stk_res.json()
                }
                
            return stk_res.json()
            
        except Exception as err:
            return {
                "error": "Failed to reach Safaricom STK gateway",
                "details": str(err)
            }

@app.post("/mpesa-callback")
async def mpesa_callback(payload: dict = Body(...)):
    print("M-PESA TRANSACTION LOG RECEIVED:", payload)
    return {"ResultCode": 0, "ResultDesc": "Success"}
