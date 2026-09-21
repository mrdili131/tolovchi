from fastapi import APIRouter, HTTPException
from models import Notification, NotificationRead
from database import Session
from services import user_dependency, PaginationParams, paginate
from schemas import NotificationResponse, PaginatedResponse, SuccessResponse
from sqlalchemy import select, or_, and_, exists, func

router = APIRouter()


@router.get('/', response_model=PaginatedResponse[NotificationResponse], status_code=200, summary="List notifications addressed to you (broadcast + targeted). ROLES: [USER, SERVICE, ADMIN]")
async def get_notifications(db: Session, user: user_dependency, params: PaginationParams):
    user_id = user.get("id")
    stmt = select(Notification).where(
        or_(Notification.target_user_id == None, Notification.target_user_id == user_id)
    ).order_by(Notification.id.desc())

    paginated = await paginate(db, stmt, params)

    read_ids = set()
    if paginated.items:
        ids = [n.id for n in paginated.items]
        rows = await db.scalars(select(NotificationRead.notification_id).where(
            NotificationRead.user_id == user_id,
            NotificationRead.notification_id.in_(ids),
        ))
        read_ids = set(rows.all())

    for n in paginated.items:
        n.is_read = n.id in read_ids
    return paginated


@router.get('/unread-count', status_code=200, summary="Count of unread notifications addressed to you. ROLES: [USER, SERVICE, ADMIN]")
async def get_unread_count(db: Session, user: user_dependency):
    user_id = user.get("id")
    unread = await db.scalar(select(func.count()).select_from(Notification).where(
        or_(Notification.target_user_id == None, Notification.target_user_id == user_id),
        ~exists().where(and_(
            NotificationRead.notification_id == Notification.id,
            NotificationRead.user_id == user_id,
        ))
    )) or 0
    return {"unread_count": unread}


@router.post('/{notification_id}/read', response_model=SuccessResponse, status_code=200, summary="Mark a notification as read. ROLES: [USER, SERVICE, ADMIN]")
async def mark_notification_read(db: Session, user: user_dependency, notification_id: int):
    user_id = user.get("id")
    notification = await db.get(Notification, notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    if notification.target_user_id is not None and notification.target_user_id != user_id:
        raise HTTPException(status_code=404, detail="Notification not found")

    existing = await db.scalar(select(NotificationRead).where(
        NotificationRead.notification_id == notification_id,
        NotificationRead.user_id == user_id,
    ))
    if not existing:
        db.add(NotificationRead(notification_id=notification_id, user_id=user_id))
        await db.commit()

    return SuccessResponse(status=True, detail="Marked as read")
