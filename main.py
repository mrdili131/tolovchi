from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from routers import main_router
from frontend import router as frontend_router
import os
from fastapi.responses import FileResponse
from services import user_dependency


app = FastAPI(title="Subscription maganer", description="This api for monthly subscription manager app", version="0.0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True
)

app.include_router(main_router, prefix="/api")
app.include_router(frontend_router)

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