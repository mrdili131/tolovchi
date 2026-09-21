from fastapi import APIRouter, HTTPException
from datetime import datetime
from models import User, UserType, Application, Transaction, TransactionStatus, Card, ApiKey, PaymentAttempt, AdminAuditLog, UserSession, PayoutRequest, PayoutStatus, Notification
from database import Session
from services import admin_role, PaginationParams, paginate
from services.payment_checker import process_application, payment_checker
from schemas import (
    UserAdminResponse, RoleUpdateForm, StatusUpdateForm, AdminUserUpdateForm,
    AdminApplicationResponse, AdminApplicationUpdateForm,
    TransactionResponse, AdminTransactionUpdateForm,
    AdminCardResponse, ApiKeyResponse, PaymentAttemptResponse,
    AuditLogResponse, AdminSessionResponse, PlatformStatsResponse,
    AdminPayoutResponse, PayoutRejectForm,
    NotificationCreateForm, NotificationResponse,
    SuccessResponse, PaginatedResponse,
)
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload

router = APIRouter()


async def log_admin_action(db: Session, admin_id: int, action: str, target_type: str, target_id: int, detail: str | None = None):
    entry = AdminAuditLog(
        admin_id=admin_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail=detail,
    )
    db.add(entry)
    await db.commit()


@router.get('/stats', response_model=PlatformStatsResponse, status_code=200, summary="Platform-wide statistics. ROLES: [ADMIN]")
async def get_stats(db: Session, user: admin_role):
    total_users = await db.scalar(select(func.count()).select_from(User).where(User.role == UserType.USER)) or 0
    total_services = await db.scalar(select(func.count()).select_from(User).where(User.role == UserType.SERVICE)) or 0
    total_admins = await db.scalar(select(func.count()).select_from(User).where(User.role == UserType.ADMIN)) or 0
    active_applications = await db.scalar(select(func.count()).select_from(Application).where(Application.is_active == True)) or 0
    total_applications = await db.scalar(select(func.count()).select_from(Application)) or 0
    total_transactions = await db.scalar(select(func.count()).select_from(Transaction)) or 0
    total_volume = await db.scalar(select(func.coalesce(func.sum(Transaction.amount), 0)).where(Transaction.status == TransactionStatus.PROVIDED)) or 0
    active_cards = await db.scalar(select(func.count()).select_from(Card).where(Card.is_active == True)) or 0
    active_api_keys = await db.scalar(select(func.count()).select_from(ApiKey).where(ApiKey.is_active == True)) or 0

    return PlatformStatsResponse(
        total_users=total_users,
        total_services=total_services,
        total_admins=total_admins,
        active_applications=active_applications,
        total_applications=total_applications,
        total_transactions=total_transactions,
        total_volume=total_volume,
        active_cards=active_cards,
        active_api_keys=active_api_keys,
    )


# ---------- Users & services ----------

@router.get('/users', response_model=PaginatedResponse[UserAdminResponse], status_code=200, summary="List users/services/admins. ROLES: [ADMIN]")
async def list_users(db: Session, user: admin_role, params: PaginationParams, role: UserType | None = None, is_active: bool | None = None, search: str | None = None):
    stmt = select(User)
    if role is not None:
        stmt = stmt.where(User.role == role)
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(or_(User.username.ilike(like), User.first_name.ilike(like), User.last_name.ilike(like)))
    stmt = stmt.order_by(User.id.desc())

    return await paginate(db, stmt, params)


@router.get('/users/{user_id}', response_model=UserAdminResponse, status_code=200, summary="Get a single user/service/admin. ROLES: [ADMIN]")
async def get_user_detail(db: Session, user: admin_role, user_id: int):
    db_user = await db.get(User, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@router.patch('/users/{user_id}/role', response_model=UserAdminResponse, status_code=200, summary="Change a user's role. ROLES: [ADMIN]")
async def update_user_role(db: Session, user: admin_role, user_id: int, form: RoleUpdateForm):
    db_user = await db.get(User, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    old_role = db_user.role.value if db_user.role else None
    db_user.role = form.role
    await db.commit()
    await db.refresh(db_user)

    await log_admin_action(db, user.get("id"), "user.role_change", "user", user_id, f"{old_role} -> {form.role.value}")
    return db_user


@router.patch('/users/{user_id}/status', response_model=UserAdminResponse, status_code=200, summary="Suspend or reactivate a user/service. ROLES: [ADMIN]")
async def update_user_status(db: Session, user: admin_role, user_id: int, form: StatusUpdateForm):
    db_user = await db.get(User, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    db_user.is_active = form.is_active
    await db.commit()
    await db.refresh(db_user)

    if not form.is_active:
        sessions = await db.scalars(select(UserSession).where(UserSession.user_id == user_id, UserSession.revoked_at == None))
        for session in sessions.all():
            session.revoked_at = datetime.utcnow()
        await db.commit()

    await log_admin_action(db, user.get("id"), "user.status_change", "user", user_id, f"is_active={form.is_active}")
    return db_user


@router.patch('/users/{user_id}', response_model=UserAdminResponse, status_code=200, summary="Edit a user's profile info (name/phone/service name). ROLES: [ADMIN]")
async def update_user_profile(db: Session, user: admin_role, user_id: int, form: AdminUserUpdateForm):
    db_user = await db.get(User, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    if form.last_name is not None:
        db_user.last_name = form.last_name
    if form.first_name is not None:
        db_user.first_name = form.first_name
    if form.middle_name is not None:
        db_user.middle_name = form.middle_name
    if form.phone_number is not None:
        db_user.phone_number = form.phone_number
    if form.service_name is not None:
        db_user.service_name = form.service_name

    await db.commit()
    await db.refresh(db_user)

    await log_admin_action(db, user.get("id"), "user.edit", "user", user_id)
    return db_user


# ---------- Applications ----------

@router.get('/applications', response_model=PaginatedResponse[AdminApplicationResponse], status_code=200, summary="List every application on the platform. ROLES: [ADMIN]")
async def list_applications(db: Session, user: admin_role, params: PaginationParams, is_active: bool | None = None, service_id: int | None = None):
    stmt = select(Application).options(selectinload(Application.payer), selectinload(Application.service))
    if is_active is not None:
        stmt = stmt.where(Application.is_active == is_active)
    if service_id is not None:
        stmt = stmt.where(Application.service_id == service_id)
    stmt = stmt.order_by(Application.id.desc())

    return await paginate(db, stmt, params)


@router.get('/applications/{application_id}', response_model=AdminApplicationResponse, status_code=200, summary="Get a single application. ROLES: [ADMIN]")
async def get_application_detail(db: Session, user: admin_role, application_id: int):
    application = await db.scalar(select(Application).where(Application.id == application_id).options(
        selectinload(Application.payer), selectinload(Application.service)
    ))
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


@router.patch('/applications/{application_id}', response_model=AdminApplicationResponse, status_code=200, summary="Edit safe fields of an application (name/description/pay_day). ROLES: [ADMIN]")
async def update_application(db: Session, user: admin_role, application_id: int, form: AdminApplicationUpdateForm):
    application = await db.get(Application, application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    if form.name is not None:
        application.name = form.name
    if form.description is not None:
        application.description = form.description
    if form.pay_day is not None:
        application.pay_day = form.pay_day

    await db.commit()
    await db.refresh(application)

    await log_admin_action(db, user.get("id"), "application.edit", "application", application_id)
    return await db.scalar(select(Application).where(Application.id == application_id).options(
        selectinload(Application.payer), selectinload(Application.service)
    ))


@router.patch('/applications/{application_id}/deactivate', response_model=AdminApplicationResponse, status_code=200, summary="Force-deactivate an application. ROLES: [ADMIN]")
async def deactivate_application(db: Session, user: admin_role, application_id: int):
    application = await db.get(Application, application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    application.is_active = False
    application.end_date = datetime.utcnow().date()
    await db.commit()
    await db.refresh(application)

    await log_admin_action(db, user.get("id"), "application.force_deactivate", "application", application_id)
    return await db.scalar(select(Application).where(Application.id == application_id).options(
        selectinload(Application.payer), selectinload(Application.service)
    ))


@router.patch('/applications/{application_id}/reactivate', response_model=AdminApplicationResponse, status_code=200, summary="Reactivate a deactivated application and clear its dunning state. ROLES: [ADMIN]")
async def reactivate_application(db: Session, user: admin_role, application_id: int):
    application = await db.get(Application, application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    application.is_active = True
    application.end_date = None
    application.failed_attempts = 0
    await db.commit()
    await db.refresh(application)

    await log_admin_action(db, user.get("id"), "application.reactivate", "application", application_id)
    return await db.scalar(select(Application).where(Application.id == application_id).options(
        selectinload(Application.payer), selectinload(Application.service)
    ))


@router.post('/applications/{application_id}/retry-charge', response_model=AdminApplicationResponse, status_code=200, summary="Manually re-run the payment attempt for one application right now. ROLES: [ADMIN]")
async def retry_application_charge(db: Session, user: admin_role, application_id: int):
    application = await db.get(Application, application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    if application.end_date:
        raise HTTPException(status_code=400, detail="Application is closed")
    if not application.payer_id:
        raise HTTPException(status_code=400, detail="Application has no payer linked yet")
    if application.is_paid:
        raise HTTPException(status_code=400, detail="Application is already paid for this cycle")

    await process_application(db, application)
    await db.refresh(application)

    await log_admin_action(db, user.get("id"), "application.retry_charge", "application", application_id)
    return await db.scalar(select(Application).where(Application.id == application_id).options(
        selectinload(Application.payer), selectinload(Application.service)
    ))


# ---------- Transactions ----------

@router.get('/transactions', response_model=PaginatedResponse[TransactionResponse], status_code=200, summary="List every transaction on the platform. ROLES: [ADMIN]")
async def list_transactions(db: Session, user: admin_role, params: PaginationParams, status: TransactionStatus | None = None, is_flagged: bool | None = None):
    stmt = select(Transaction).options(
        selectinload(Transaction.sender), selectinload(Transaction.receiver), selectinload(Transaction.application)
    )
    if status is not None:
        stmt = stmt.where(Transaction.status == status)
    if is_flagged is not None:
        stmt = stmt.where(Transaction.is_flagged == is_flagged)
    stmt = stmt.order_by(Transaction.id.desc())

    return await paginate(db, stmt, params)


@router.patch('/transactions/{transaction_id}', response_model=TransactionResponse, status_code=200, summary="Flag/annotate/mark a transaction as refunded. ROLES: [ADMIN]")
async def update_transaction(db: Session, user: admin_role, transaction_id: int, form: AdminTransactionUpdateForm):
    transaction = await db.get(Transaction, transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    if form.is_flagged is not None:
        transaction.is_flagged = form.is_flagged
    if form.admin_note is not None:
        transaction.admin_note = form.admin_note
    if form.mark_refunded:
        transaction.refunded_at = datetime.utcnow().date()

    await db.commit()
    await db.refresh(transaction)

    await log_admin_action(db, user.get("id"), "transaction.annotate", "transaction", transaction_id)
    return await db.scalar(select(Transaction).where(Transaction.id == transaction_id).options(
        selectinload(Transaction.sender), selectinload(Transaction.receiver), selectinload(Transaction.application)
    ))


# ---------- Cards ----------

@router.get('/cards', response_model=PaginatedResponse[AdminCardResponse], status_code=200, summary="List every bound card on the platform. ROLES: [ADMIN]")
async def list_cards(db: Session, user: admin_role, params: PaginationParams, is_active: bool | None = None):
    stmt = select(Card).options(selectinload(Card.user))
    if is_active is not None:
        stmt = stmt.where(Card.is_active == is_active)
    stmt = stmt.order_by(Card.id.desc())

    return await paginate(db, stmt, params)


@router.patch('/cards/{card_id}/deactivate', response_model=AdminCardResponse, status_code=200, summary="Force-deactivate a card. ROLES: [ADMIN]")
async def deactivate_card(db: Session, user: admin_role, card_id: int):
    card = await db.get(Card, card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    card.is_active = False
    await db.commit()
    await db.refresh(card)

    await log_admin_action(db, user.get("id"), "card.deactivate", "card", card_id)
    return await db.scalar(select(Card).where(Card.id == card_id).options(selectinload(Card.user)))


# ---------- Developer API keys ----------

@router.get('/api-keys', response_model=PaginatedResponse[ApiKeyResponse], status_code=200, summary="List every service's API keys. ROLES: [ADMIN]")
async def list_api_keys(db: Session, user: admin_role, params: PaginationParams, service_id: int | None = None):
    stmt = select(ApiKey)
    if service_id is not None:
        stmt = stmt.where(ApiKey.service_id == service_id)
    stmt = stmt.order_by(ApiKey.id.desc())

    return await paginate(db, stmt, params)


@router.post('/api-keys/{key_id}/revoke', response_model=SuccessResponse, status_code=200, summary="Revoke a service's API key. ROLES: [ADMIN]")
async def revoke_api_key(db: Session, user: admin_role, key_id: int):
    key = await db.get(ApiKey, key_id)
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")

    key.is_active = False
    key.revoked_at = datetime.utcnow().date()
    await db.commit()

    await log_admin_action(db, user.get("id"), "api_key.revoke", "api_key", key_id)
    return SuccessResponse(status=True, detail="API key revoked")


# ---------- Logs ----------

@router.get('/payment-attempts', response_model=PaginatedResponse[PaymentAttemptResponse], status_code=200, summary="The dunning job's attempt log. ROLES: [ADMIN]")
async def list_payment_attempts(db: Session, user: admin_role, params: PaginationParams, application_id: int | None = None, success: bool | None = None):
    stmt = select(PaymentAttempt)
    if application_id is not None:
        stmt = stmt.where(PaymentAttempt.application_id == application_id)
    if success is not None:
        stmt = stmt.where(PaymentAttempt.success == success)
    stmt = stmt.order_by(PaymentAttempt.id.desc())

    return await paginate(db, stmt, params)


@router.get('/audit-log', response_model=PaginatedResponse[AuditLogResponse], status_code=200, summary="The admin action audit log. ROLES: [ADMIN]")
async def list_audit_log(db: Session, user: admin_role, params: PaginationParams):
    stmt = select(AdminAuditLog).order_by(AdminAuditLog.id.desc())
    return await paginate(db, stmt, params)


# ---------- Sessions ----------

@router.get('/sessions', response_model=PaginatedResponse[AdminSessionResponse], status_code=200, summary="View every login session on the platform. ROLES: [ADMIN]")
async def list_sessions(db: Session, user: admin_role, params: PaginationParams, user_id: int | None = None, is_revoked: bool | None = None):
    stmt = select(UserSession).options(selectinload(UserSession.user))
    if user_id is not None:
        stmt = stmt.where(UserSession.user_id == user_id)
    if is_revoked is not None:
        stmt = stmt.where(UserSession.revoked_at != None) if is_revoked else stmt.where(UserSession.revoked_at == None)
    stmt = stmt.order_by(UserSession.id.desc())

    return await paginate(db, stmt, params)


@router.post('/sessions/{session_id}/revoke', response_model=SuccessResponse, status_code=200, summary="Forcibly log out one session (any user). ROLES: [ADMIN]")
async def revoke_session(db: Session, user: admin_role, session_id: int):
    session = await db.get(UserSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.revoked_at = datetime.utcnow()
    await db.commit()

    await log_admin_action(db, user.get("id"), "session.revoke", "session", session_id)
    return SuccessResponse(status=True, detail="Session revoked")


# ---------- Payouts ----------

@router.get('/payouts', response_model=PaginatedResponse[AdminPayoutResponse], status_code=200, summary="List every service's payout requests. ROLES: [ADMIN]")
async def list_payouts(db: Session, user: admin_role, params: PaginationParams, status: str | None = None):
    stmt = select(PayoutRequest).options(selectinload(PayoutRequest.service))
    if status is not None:
        stmt = stmt.where(PayoutRequest.status == status)
    stmt = stmt.order_by(PayoutRequest.id.desc())

    return await paginate(db, stmt, params)


@router.patch('/payouts/{payout_id}/pay', response_model=AdminPayoutResponse, status_code=200, summary="Mark a payout as paid out and deduct it from the service's balance. ROLES: [ADMIN]")
async def pay_payout(db: Session, user: admin_role, payout_id: int):
    payout = await db.get(PayoutRequest, payout_id)
    if not payout:
        raise HTTPException(status_code=404, detail="Payout request not found")
    if payout.status != PayoutStatus.PENDING.value:
        raise HTTPException(status_code=400, detail="This payout request has already been processed")

    service = await db.get(User, payout.service_id)
    if not service or service.balance < payout.amount:
        raise HTTPException(status_code=400, detail="Service no longer has sufficient balance for this payout")

    service.balance -= payout.amount
    payout.status = PayoutStatus.PAID.value
    payout.processed_at = datetime.utcnow().date()
    payout.processed_by = user.get("id")

    await db.commit()
    await db.refresh(payout)

    await log_admin_action(db, user.get("id"), "payout.pay", "payout", payout_id, f"amount={payout.amount}")
    return await db.scalar(select(PayoutRequest).where(PayoutRequest.id == payout_id).options(selectinload(PayoutRequest.service)))


@router.patch('/payouts/{payout_id}/reject', response_model=AdminPayoutResponse, status_code=200, summary="Reject a payout request. ROLES: [ADMIN]")
async def reject_payout(db: Session, user: admin_role, payout_id: int, form: PayoutRejectForm):
    payout = await db.get(PayoutRequest, payout_id)
    if not payout:
        raise HTTPException(status_code=404, detail="Payout request not found")
    if payout.status != PayoutStatus.PENDING.value:
        raise HTTPException(status_code=400, detail="This payout request has already been processed")

    payout.status = PayoutStatus.REJECTED.value
    payout.admin_note = form.admin_note
    payout.processed_at = datetime.utcnow().date()
    payout.processed_by = user.get("id")

    await db.commit()
    await db.refresh(payout)

    await log_admin_action(db, user.get("id"), "payout.reject", "payout", payout_id)
    return await db.scalar(select(PayoutRequest).where(PayoutRequest.id == payout_id).options(selectinload(PayoutRequest.service)))


# ---------- Notifications ----------

@router.post('/notifications', response_model=NotificationResponse, status_code=201, summary="Send a notification — broadcast to everyone, or targeted at one user by id. ROLES: [ADMIN]")
async def send_notification(db: Session, user: admin_role, form: NotificationCreateForm):
    if form.target_user_id is not None:
        target = await db.get(User, form.target_user_id)
        if not target:
            raise HTTPException(status_code=404, detail="Target user not found")

    notification = Notification(
        title=form.title,
        message=form.message,
        target_user_id=form.target_user_id,
        created_by=user.get("id"),
    )
    db.add(notification)
    await db.commit()
    await db.refresh(notification)

    await log_admin_action(
        db, user.get("id"), "notification.send", "notification", notification.id,
        f"target={form.target_user_id or 'all'}"
    )
    return notification


# ---------- Billing ----------

@router.post('/run-billing-cycle', response_model=SuccessResponse, status_code=200, summary="Immediately run the dunning job for every application that's currently due or pending, instead of waiting for the 8am schedule. ROLES: [ADMIN]")
async def run_billing_cycle(db: Session, user: admin_role):
    await payment_checker(db)
    await log_admin_action(db, user.get("id"), "billing.run_cycle", "system", 0)
    return SuccessResponse(status=True, detail="Billing cycle finished")
