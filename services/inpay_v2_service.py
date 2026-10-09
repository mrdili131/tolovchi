import os, uuid, asyncio, logging, httpx
from dotenv import load_dotenv
from fastapi import HTTPException


load_dotenv()

logger = logging.getLogger(__name__)

INPAY_V2_BASE_URL = "https://inpay.uz/api/v2"
INPAY_V2_TIMEOUT_SECONDS = 15

# How long to wait for a charge stuck in `processing` before cancelling it.
CHARGE_STATUS_POLLS = 3
CHARGE_STATUS_POLL_SECONDS = 2


SERVICE_ERROR_PREFIX = "SERVICE ERROR: "

# Errors caused by our own InPay setup (key, IP whitelist, inactive merchant):
# the user can't fix these, so don't show them InPay's technical text.
CONFIG_ERROR_CODES = {"missing_authorization", "invalid_api_key", "merchant_inactive", "domain_not_whitelisted"}

FRIENDLY_MESSAGES = {
    "resource_missing": "Karta topilmadi yoki allaqachon o'chirilgan.",
    "rate_limit": "So'rovlar juda ko'p. Birozdan so'ng qayta urinib ko'ring.",
}


class InpayV2Error(HTTPException):
    def __init__(self, code: str | None, message: str | None, status_code: int = 400):
        super().__init__(status_code=status_code, detail=f"{SERVICE_ERROR_PREFIX}{message or 'To‘lov tizimida xatolik yuz berdi.'}")
        self.code = code


def _error_from_response(http_status: int, error: dict) -> InpayV2Error:
    code = error.get("code")
    if code in CONFIG_ERROR_CODES or http_status in (401, 403):
        return InpayV2Error(code, "To‘lov tizimi bilan ulanishda sozlama xatosi. Qo‘llab-quvvatlash xizmatiga murojaat qiling.", 502)
    if http_status == 429:
        return InpayV2Error(code, FRIENDLY_MESSAGES["rate_limit"], 429)
    if http_status >= 500:
        return InpayV2Error(code, error.get("message") or "To‘lov tizimida vaqtinchalik nosozlik. Birozdan so‘ng qayta urinib ko‘ring.", 502)
    if http_status == 404:
        return InpayV2Error(code, FRIENDLY_MESSAGES["resource_missing"], 404)
    return InpayV2Error(code, FRIENDLY_MESSAGES.get(code) or error.get("message"), 400)


class InpayV2Service:
    """InPay API v2 client (https://inpay.uz/api/v2/).

    Card binding is two-step: create_card() sends an SMS code to the card
    owner's phone, verify_card() confirms it and the card becomes `active`.
    charge() takes money from a saved card without the customer present."""

    def __init__(self, secret_key=None):
        self.secret_key = secret_key or os.getenv("V2_API_KEY")
        if not self.secret_key:
            logger.error("V2_API_KEY is not configured")
            raise InpayV2Error("missing_authorization", "To‘lov tizimi sozlanmagan. Qo‘llab-quvvatlash xizmatiga murojaat qiling.", 503)

    async def _request(self, method, path, json=None, params=None, idempotency_key=None):
        headers = {"Authorization": f"Bearer {self.secret_key}"}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        try:
            async with httpx.AsyncClient(base_url=INPAY_V2_BASE_URL, timeout=INPAY_V2_TIMEOUT_SECONDS) as client:
                r = await client.request(method, path, headers=headers, json=json, params=params)
        except httpx.TimeoutException:
            logger.warning(f"{method} {path} -> timeout")
            raise InpayV2Error("timeout", "To‘lov tizimi javob bermadi. Birozdan so‘ng qayta urinib ko‘ring.", 504)
        except httpx.HTTPError as exc:
            logger.warning(f"{method} {path} -> {type(exc).__name__}")
            raise InpayV2Error("unreachable", "To‘lov tizimi bilan bog‘lanib bo‘lmadi. Birozdan so‘ng qayta urinib ko‘ring.", 502)

        try:
            body = r.json()
        except ValueError:
            logger.warning(f"{method} {path} -> {r.status_code} non-JSON response")
            raise InpayV2Error("invalid_response", "To‘lov tizimidan noto‘g‘ri javob keldi. Birozdan so‘ng qayta urinib ko‘ring.", 502)

        if not body.get("success"):
            error = body.get("error") or {}
            logger.warning(f"{method} {path} -> {r.status_code} {error.get('code')} ({error.get('request_id')})")
            raise _error_from_response(r.status_code, error)
        return body["data"]

    async def create_customer(self, user_id: int, name: str | None = None, phone: str | None = None):
        body = {"metadata": {"bindin_user_id": str(user_id)}}
        if name:
            body["name"] = name
        if phone:
            body["phone"] = phone
        # Same key for the same user: a retried request can't create a duplicate customer.
        return await self._request("POST", "/customers/", json=body, idempotency_key=f"bindin-customer-{user_id}")

    async def create_card(self, card_number: str, expire_date: str, customer_id: str | None = None):
        body = {"card_number": card_number, "expire_date": expire_date}
        if customer_id:
            body["customer_id"] = customer_id
        return await self._request("POST", "/payment-methods/card/create.php", json=body, idempotency_key=str(uuid.uuid4()))

    async def verify_card(self, payment_method_id: str, code: str):
        return await self._request("POST", "/payment-methods/card/verify.php", json={
            "id": payment_method_id,
            "code": code,
        })

    async def get_card(self, payment_method_id: str):
        """Returns the card, or None if InPay no longer has it (detached)."""
        try:
            data = await self._request("GET", "/payment-methods/", params={"id": payment_method_id})
        except InpayV2Error as exc:
            if exc.code == "resource_missing":
                return None
            raise
        if data.get("object") == "list":
            return data["data"][0] if data.get("data") else None
        return data

    async def remove_card(self, payment_method_id: str):
        data = await self._request("DELETE", "/payment-methods/", params={"id": payment_method_id})
        return data.get("status") == "detached"

    async def charge(self, payment_method_id: str, customer_id: str | None, amount: int, idempotency_key: str,
                     description: str | None = None, metadata: dict | None = None):
        """Charges a saved card right away. Returns the payment when it
        succeeded, raises InpayV2Error otherwise — a payment that didn't
        succeed is cancelled so it can't be completed later behind our back."""
        body = {"amount": amount, "payment_method": payment_method_id, "confirm": True, "metadata": metadata or {}}
        if customer_id:
            body["customer"] = customer_id
        if description:
            body["description"] = description

        payment = await self._request("POST", "/payments/", json=body, idempotency_key=idempotency_key)

        for _ in range(CHARGE_STATUS_POLLS):
            if payment.get("status") not in ("processing", "requires_action"):
                break
            await asyncio.sleep(CHARGE_STATUS_POLL_SECONDS)
            payment = await self._request("GET", f"/payments/{payment['id']}")

        if payment.get("status") in ("requires_payment_method", "processing", "requires_action"):
            try:
                payment = await self._request("POST", f"/payments/{payment['id']}/cancel")
            except InpayV2Error as exc:
                if exc.code != "invalid_state":
                    raise
                # Settled while we were cancelling — take whatever it ended up as.
                payment = await self._request("GET", f"/payments/{payment['id']}")

        if payment.get("status") != "succeeded":
            logger.warning(f"charge {payment.get('id')} ended as {payment.get('status')}")
            raise InpayV2Error(payment.get("status"), "Kartadan pul yechib bo‘lmadi (mablag‘ yetarli emas yoki karta faol emas).", 402)
        return payment


async def ensure_inpay_customer(db, inpay: InpayV2Service, user) -> str:
    """Returns the user's InPay customer id, creating the customer on first use."""
    if user.inpay_customer_id:
        return user.inpay_customer_id
    name = " ".join(part for part in [user.last_name, user.first_name] if part) or user.username
    customer = await inpay.create_customer(user.id, name=name, phone=user.phone_number)
    user.inpay_customer_id = customer["id"]
    await db.commit()
    return user.inpay_customer_id


async def charge_saved_card(inpay: InpayV2Service, payer, card, amount: int, transaction, description: str):
    """Charges `card` for `transaction` and records InPay's payment id on it.
    The idempotency key is tied to the transaction, so a retried request can
    never charge the same transaction twice."""
    payment = await inpay.charge(
        payment_method_id=card.charge_id,
        customer_id=payer.inpay_customer_id if payer else None,
        amount=amount,
        idempotency_key=f"bindin-txn-{transaction.id}",
        description=description,
        metadata={"transaction_id": str(transaction.id), "application_id": str(transaction.application_id)},
    )
    transaction.gateway_payment_id = payment["id"]
    return payment
