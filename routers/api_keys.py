from fastapi import APIRouter, HTTPException
from datetime import datetime
from models import ApiKey, PayoutRequest, User
from database import Session
from services import service_role, generate_api_key, validate_payout_request, PaginationParams, paginate
from schemas import (
    ApiKeyCreateForm, ApiKeyCreateResponse, ApiKeyResponse,
    PayoutCreateForm, PayoutResponse,
    WebhookUpdateForm, ServiceResponse,
    SuccessResponse, PaginatedResponse,
)
from sqlalchemy import select

router = APIRouter()


@router.get('/keys', response_model=PaginatedResponse[ApiKeyResponse], status_code=200, summary="List your own API keys. ROLES: [SERVICE]")
async def list_keys(db: Session, user: service_role, params: PaginationParams):
    stmt = select(ApiKey).where(ApiKey.service_id == user.get("id")).order_by(ApiKey.id.desc())
    return await paginate(db, stmt, params)


@router.post('/keys', response_model=ApiKeyCreateResponse, status_code=201, summary="Generate a new API key. The full key is only ever shown once. ROLES: [SERVICE]")
async def create_key(db: Session, user: service_role, form: ApiKeyCreateForm):
    raw_key, prefix, key_hash = generate_api_key()

    new_key = ApiKey(
        service_id=user.get("id"),
        name=form.name,
        key_prefix=prefix,
        key_hash=key_hash,
    )
    db.add(new_key)
    await db.commit()
    await db.refresh(new_key)

    return ApiKeyCreateResponse(
        id=new_key.id,
        name=new_key.name,
        key_prefix=new_key.key_prefix,
        is_active=new_key.is_active,
        last_used_at=new_key.last_used_at,
        revoked_at=new_key.revoked_at,
        created_at=new_key.created_at,
        key=raw_key,
    )


@router.post('/keys/{key_id}/revoke', response_model=SuccessResponse, status_code=200, summary="Revoke one of your own API keys. ROLES: [SERVICE]")
async def revoke_key(db: Session, user: service_role, key_id: int):
    key = await db.scalar(select(ApiKey).where(ApiKey.id == key_id, ApiKey.service_id == user.get("id")))
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")

    key.is_active = False
    key.revoked_at = datetime.utcnow().date()
    await db.commit()

    return SuccessResponse(status=True, detail="API key revoked")


@router.delete('/keys/{key_id}', response_model=SuccessResponse, status_code=200, summary="Permanently delete one of your own API keys. ROLES: [SERVICE]")
async def delete_key(db: Session, user: service_role, key_id: int):
    key = await db.scalar(select(ApiKey).where(ApiKey.id == key_id, ApiKey.service_id == user.get("id")))
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")

    await db.delete(key)
    await db.commit()

    return SuccessResponse(status=True, detail="API key deleted")


# ---------- Payouts ----------

@router.get('/payouts', response_model=PaginatedResponse[PayoutResponse], status_code=200, summary="List your own payout requests. ROLES: [SERVICE]")
async def list_my_payouts(db: Session, user: service_role, params: PaginationParams):
    stmt = select(PayoutRequest).where(PayoutRequest.service_id == user.get("id")).order_by(PayoutRequest.id.desc())
    return await paginate(db, stmt, params)


@router.post('/payouts', response_model=PayoutResponse, status_code=201, summary="Request a payout from your balance to a bank card. Minimum 100,000 so'm, one request per calendar month. ROLES: [SERVICE]")
async def request_payout(db: Session, user: service_role, form: PayoutCreateForm):
    service = await db.get(User, user.get("id"))
    if not service:
        raise HTTPException(status_code=404, detail="Service account not found")

    await validate_payout_request(db, service, form.amount)

    payout = PayoutRequest(
        service_id=service.id,
        amount=form.amount,
        card_number=form.card_number,
    )
    db.add(payout)
    await db.commit()
    await db.refresh(payout)

    return payout


# ---------- Webhook ----------

@router.patch('/webhook', response_model=ServiceResponse, status_code=200, summary="Set or clear the URL that receives application/payment event callbacks. ROLES: [SERVICE]")
async def update_webhook(db: Session, user: service_role, form: WebhookUpdateForm):
    service = await db.get(User, user.get("id"))
    if not service:
        raise HTTPException(status_code=404, detail="Service account not found")

    service.webhook_url = form.webhook_url
    await db.commit()
    await db.refresh(service)

    return service
