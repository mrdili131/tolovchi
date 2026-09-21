import httpx
from datetime import datetime

WEBHOOK_TIMEOUT_SECONDS = 5


async def send_webhook(service_webhook_url: str | None, event: str, payload: dict):
    """Best-effort callback to a service's registered webhook URL. Never raises —
    a service's endpoint being down/slow must not break the billing flow."""
    if not service_webhook_url:
        return

    body = {"event": event, "sent_at": datetime.utcnow().isoformat(), **payload}

    try:
        async with httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT_SECONDS) as client:
            await client.post(service_webhook_url, json=body)
    except Exception as e:
        print(f"[WEBHOOK] Failed to deliver '{event}' to {service_webhook_url}: {e}")
