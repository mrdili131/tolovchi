from fastapi import APIRouter
from .user import router as user_router
from .application import router as application_router
from .card import router as card_router
from .transaction import router as transaction_router
from .admin import router as admin_router
from .api_keys import router as api_key_router
from .notification import router as notification_router


main_router = APIRouter()

main_router.include_router(user_router,prefix="/auth",tags=["Authorization"])
main_router.include_router(application_router,prefix="/application",tags=["Application"])
main_router.include_router(card_router,prefix="/card",tags=["Card"])
main_router.include_router(transaction_router,prefix="/transaction",tags=["Transaction"])
main_router.include_router(admin_router,prefix="/admin",tags=["Admin"])
main_router.include_router(api_key_router,prefix="/developer",tags=["Developer"])
main_router.include_router(notification_router,prefix="/notifications",tags=["Notifications"])

