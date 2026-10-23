from starlette.middleware.sessions import SessionMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi import APIRouter, FastAPI, Request
from pathlib import Path

from app.core.config import Settings, get_settings
from app.core.security import require_session_secret
from app.routers import api, auth
from app.api.v1.endpoints import phone_numbers
from app.db.base import Base, engine
from app.services.monitor import init_monitoring, schedule_active_numbers

SESSION_MAX_AGE_SECONDS = 7 * 24 * 60 * 60  # 1 week

# Templates
templates_dir = Path(__file__).parent / "templates"
templates_dir.mkdir(exist_ok=True)
templates = Jinja2Templates(directory=str(templates_dir))

pages = APIRouter()

@pages.get("/")
async def home(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": "Caller ID Monitor"
        }
    )

@pages.get("/branded")
async def branded(request: Request):
    return templates.TemplateResponse(
        "branded.html",
        {
            "request": request,
            "title": "Branded Caller ID"
        }
    )

@pages.get("/pricing")
async def pricing(request: Request):
    return templates.TemplateResponse(
        "pricing.html",
        {
            "request": request,
            "title": "Pricing"
        }
    )

@pages.get("/settings")
async def settings_page(request: Request):
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "title": "Settings"
        }
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    session_secret = require_session_secret(settings.SESSION_SECRET)

    app = FastAPI()

    @app.on_event("startup")
    async def startup():
        # Create database tables
        Base.metadata.create_all(bind=engine)
        # Initialize the monitoring scheduler and resume monitoring with each owner's key
        init_monitoring()
        schedule_active_numbers()

    app.add_middleware(
        SessionMiddleware,
        secret_key=session_secret,
        max_age=SESSION_MAX_AGE_SECONDS,
    )

    # Mount static files
    static_dir = Path(__file__).parent / "static"
    static_dir.mkdir(exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # API routers
    app.include_router(api.router)
    app.include_router(auth.router)
    app.include_router(phone_numbers.router, prefix="/api/v1/phone-numbers", tags=["phone-numbers"])
    app.include_router(pages)

    return app


app = create_app()
