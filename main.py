import base64
from datetime import datetime
import httpx
import os
from fastapi import FastAPI, Body

app = FastAPI()

# ==================== PASTE YOUR ACTUAL DARAJA KEYS HERE ====================
CONSUMER_KEY = "vZNe6HBgVSab6vUpMjZRETF7TDhmjrZa8Rar9fKCoMa4GoYw"
CONSUMER_SECRET = "msRw8mymJCG8clfbpDGnCnGrdJnhycnbInnpwwU58dsh1aVhIvYfxqt2lCFruNiS"
# ============================================================================

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

    # 2. Fetch a fresh, valid token automatically using standard Basic Auth
    auth_url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    
    async with httpx.AsyncClient() as client:
        try:
            # Using basic auth tuple handles the encoding natively without header bugs
            token_res = await client.get(auth_url, auth=(CONSUMER_KEY.strip(), CONSUMER_SECRET.strip()))
            
            if token_res.status_code != 200:
                return {
                    "error": "Safaricom rejected your credentials",
                    "status_code": token_res.status_code,
                    "safaricom_msg": token_res.text
                }
                
            token = token_res.json()["access_token"]
            
        except Exception as err:
            return {"error": "OAuth Handshake Failed", "details": str(err)}

    # 3. Request the STK Push
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
    
    try:
        stk_res = await client.post(stk_url, json=payload, headers=headers)
        return stk_res.json()
    except Exception as err:
        return {"error": "STK Push Request Failed", "details": str(err)}

@app.post("/mpesa-callback")
async def mpesa_callback(payload: dict = Body(...)):
    print("M-PESA TRANSACTION LOG RECEIVED:", payload)
    return {"ResultCode": 0, "ResultDesc": "Success"}
