import requests
import time, json, hmac, hashlib, secrets, requests
from dotenv import load_dotenv
import os
import random


load_dotenv()

class InpayAutoPayService:
    def __init__(self):
        self.access_token = None

        r = requests.post("https://inpay.uz/api/v1/authorization/",params={
            "merchant_id":os.getenv("MERCHANT_ID"),
            "merchant_token":os.getenv("MERCHANT_TOKEN")
        })
        if not r.ok:
            raise TypeError("Cannot get access token")
        self.access_token = r.json()["bearer_token"]


    def inpay_cards(self, action, body, key_id, secret):
        path  = f'/api/v1/cards/{action}'
        raw   = json.dumps(body, ensure_ascii=False)
        ts    = str(int(time.time()))
        nonce = secrets.token_hex(12)
        base  = f"POST\n{path}\n{ts}\n{nonce}\n" + hashlib.sha256(raw.encode()).hexdigest()
        sig   = hmac.new(secret.encode(), base.encode(), hashlib.sha256).hexdigest()
        return requests.post(
            f"https://inpay.uz{path}", data=raw.encode(),
            headers={'Content-Type': 'application/json', 'X-Inpay-Key': key_id,
                    'X-Inpay-Timestamp': ts, 'X-Inpay-Nonce': nonce,
                    'X-Inpay-Signature': sig}, timeout=30)


    def order(self,amount: int):
        r = requests.post("https://inpay.uz/api/v1/create",
        headers={
            "Authorization":f"Bearer {self.access_token}"
        },
        json={
            "merchant_id":os.getenv("MERCHANT_ID"),
            "token":os.getenv("MERCHANT_TOKEN"),
            "amount":amount
        })
        if not r.ok:
            raise TypeError("Cannot create order")
        return r.json()["cardsystem_order_id"]


    def bind(self,customer_id="99160133"):
        r = self.inpay_cards(
            action = "bind",
            body = {"customer_ref":customer_id}, # Customer ID ni to‘g‘irlang
            key_id = os.getenv("INPAY_KEY_ID"),
            secret = os.getenv("INPAY_CARD_SECRET")
        ).json()
        if r["success"] == False:
            raise TypeError("Cannot generate card link page")
        return r

    def charge(self,card_id,amount):
        r = self.inpay_cards(
            action = "charge",
            body = {
                "card_id":card_id,
                "amount":amount,
                "idem_key":random.randint(1000,9999), # Memorial order [NEEDS TO BE CHANGED]
                "reason":"Avto-to‘lov"
            },
            key_id = os.getenv("INPAY_KEY_ID"),
            secret = os.getenv("INPAY_CARD_SECRET")
        )
        match r.status_code:
            case 400:
                raise TypeError("Summa yechishda xatolik")
            case 402:
                raise TypeError("Bank kartasi faol emas")
            case 401:
                raise TypeError("Imzoda xatolik")
            case _:
                r = r.json()
                if r["success"] == False:
                    raise TypeError("Could not get amount")
                return r
            

# print(InpayAutoPayService().bind())
# print(InpayAutoPayService().charge(38,1000))