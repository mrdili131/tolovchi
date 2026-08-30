from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from routers import main_router
from frontend import router as frontend_router
import os
from fastapi.responses import FileResponse
from services import user_dependency


app = FastAPI(title="Subscription maganer", description="This api for monthly subscription manager app", version="0.0.1")

app.mount('/static', StaticFiles(directory='frontend/static'),name='static')

app.include_router(main_router, prefix="/api")
app.include_router(frontend_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://test-c401bb6e.fastapicloud.dev",
        "http://magazinjon.uz",
        "https://magazinjon.uz",
        "http://127.0.0.1:8000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

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