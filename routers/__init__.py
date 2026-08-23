from fastapi import APIRouter
from .user import router as user_router
from .application import router as application_router

main_router = APIRouter()

main_router.include_router(user_router,prefix="/auth",tags=["Authorization"])
main_router.include_router(application_router,prefix="/application",tags=["Application"])