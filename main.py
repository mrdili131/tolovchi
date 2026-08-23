from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import main_router


app = FastAPI(title="Subscription maganer", description="This api for monthly subscription manager app", version="0.0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True
)

app.include_router(main_router, prefix="/api")

@app.get('/health', include_in_schema=False)
def health():
    return {"health":"good"}


# Dilmuhammad Abdukodirov 2026