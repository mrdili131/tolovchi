import logging
import time
from routers import main_router
from scheduler import lifespan_scheduler
import html
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse
from fastapi.exception_handlers import http_exception_handler
from starlette.exceptions import HTTPException as StarletteHTTPException
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

app = FastAPI(title="Subscription manager",
                description="This api for monthly subscription manager app",
                version="0.0.1",
                lifespan=lifespan_scheduler,
                docs_url=None,
                redoc_url=None
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


ERROR_TEMPLATE = open("frontend/templates/error.html", encoding="utf-8").read()

ERROR_TEXTS = {
    401: ("Kirish talab qilinadi", "Bu sahifani ko‘rish uchun hisobingizga kiring."),
    403: ("Ruxsat yo‘q", "Sizda bu sahifani ko‘rish uchun ruxsat yo‘q."),
    404: ("Sahifa topilmadi", "Siz qidirgan sahifa mavjud emas yoki boshqa manzilga ko‘chirilgan."),
    405: ("So‘rov usuli noto‘g‘ri", "Bu manzil bunday so‘rovni qabul qilmaydi."),
    500: ("Serverda xatolik", "Kutilmagan xatolik yuz berdi. Birozdan keyin qayta urinib ko‘ring."),
}


def wants_html(request: Request) -> bool:
    # API clients always get JSON; only browser page loads get the HTML error page.
    if request.url.path.startswith("/api"):
        return False
    return "text/html" in request.headers.get("accept", "")


def render_error_page(status_code: int) -> HTMLResponse:
    title, message = ERROR_TEXTS.get(status_code, ("Xatolik yuz berdi", "So‘rovni bajarib bo‘lmadi. Birozdan keyin qayta urinib ko‘ring."))
    page = (ERROR_TEMPLATE
            .replace("{{code}}", str(status_code))
            .replace("{{title}}", html.escape(title))
            .replace("{{message}}", html.escape(message)))
    return HTMLResponse(page, status_code=status_code)


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request: Request, exc: StarletteHTTPException):
    if wants_html(request):
        return render_error_page(exc.status_code)
    # Everything else (API, mobile app) gets FastAPI's stock response, unchanged.
    return await http_exception_handler(request, exc)


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error on {request.method} {request.url.path}")
    if wants_html(request):
        return render_error_page(500)
    # Same body Starlette sent before this handler existed.
    return PlainTextResponse("Internal Server Error", status_code=500)


@app.get('/health', include_in_schema=False)
def health():
    return {"health":"good"}


@app.get('/sitemap.xml', include_in_schema=False)
def sitemap():
    return FileResponse("sitemap.xml")

@app.get('/robots.txt', include_in_schema=False)
def robots():
    return FileResponse("robots.txt")

# Dilmuhammad Abdukodirov 2026