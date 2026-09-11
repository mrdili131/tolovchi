import os
import logging
import time
from routers import main_router
from services import user_dependency
from scheduler import lifespan_scheduler
from fastapi.responses import FileResponse
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from frontend import router as frontend_router
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(
    level=logging.INFO,
    format = "%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler("logs/bindin.log",encoding="utf-8")
    ]
)

logger = logging.getLogger(__name__)

app = FastAPI(title="Subscription maganer",
                description="This api for monthly subscription manager app",
                version="0.0.1",
                lifespan=lifespan_scheduler
            )

app.mount('/static', StaticFiles(directory='frontend/static'),name='static')

app.include_router(main_router, prefix="/api")
app.include_router(frontend_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://test-c401bb6e.fastapicloud.dev",
        "http://bindin.uz",
        "https://bindin.uz",
        "http://127.0.0.1:8000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    response_time = time.perf_counter() - start_time
    logger.info(f"{request.method} {request.url.path} {response.status_code} {response_time:.3f}s")
    return response


@app.get('/health', include_in_schema=False)
def health():
    return {"health":"good"}


@app.get('/db', summary="ADMIN ACCESS ONLY !!!")
async def download_db(user: user_dependency):
    if not user.get("role") == "admin":
        raise HTTPException(status_code=404,detail="Only admin access")
    try:
        return FileResponse(
            path=os.path.join("musha.db"),
            filename="musha.db",
            media_type="application/octet-stream",
            content_disposition_type="attachment"
        )
    except:
        raise HTTPException(status_code=404, detail="Database not found")

# Dilmuhammad Abdukodirov 2026